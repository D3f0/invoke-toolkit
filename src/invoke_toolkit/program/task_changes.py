"""Compare loaded task definitions with their Git HEAD source, without executing it."""

import ast
import inspect
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from invoke.collection import Collection
from invoke.exceptions import Exit

Change = Literal["new", "updated"]


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(path.parent), *args], capture_output=True, check=False
        )
    except OSError as error:
        raise Exit("Git is required for --list-changed.", code=1) from error


def _head_source(path: Path) -> bytes:
    root = _git(path, "rev-parse", "--show-toplevel")
    if root.returncode:
        raise Exit("--list-changed requires a task file in a Git repository.", code=1)
    relative = path.relative_to(Path(os.fsdecode(root.stdout).rstrip("\n")).resolve())
    if _git(path, "rev-parse", "--verify", "--quiet", "HEAD").returncode:
        return b""
    tree = _git(
        path,
        "ls-tree",
        "--full-tree",
        "-z",
        "HEAD",
        "--",
        f":(literal){relative.as_posix()}",
    )
    if tree.returncode:
        raise Exit("Unable to read task file history from Git HEAD.", code=1)
    if not tree.stdout:
        return b""
    source = _git(path, "show", f"HEAD:{relative.as_posix()}")
    if source.returncode:
        raise Exit("Unable to read task file from Git HEAD.", code=1)
    return source.stdout


def _module_functions(
    node: ast.AST,
) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Find module-scope functions, including control flow but excluding nested scopes."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        yield node
    elif not isinstance(node, (ast.ClassDef, ast.Lambda)):
        for child in ast.iter_child_nodes(node):
            yield from _module_functions(child)


def _task_decorated(
    node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module
) -> bool:
    """Recognize task decorators, including imported aliases, without execution."""
    names = {"task"}
    for item in ast.walk(tree):
        if isinstance(item, ast.ImportFrom) and item.module in {
            "invoke_toolkit",
            "invoke",
            "invoke.tasks",
            "invoke_toolkit.tasks",
        }:
            names.update(
                alias.asname or alias.name
                for alias in item.names
                if alias.name == "task"
            )
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id in names:
            return True
        if isinstance(target, ast.Attribute) and target.attr == "task":
            return True
    pending: list[ast.AST] = []
    pending.extend(tree.body)
    while pending:
        item = pending.pop()
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(item, (ast.Assign, ast.AnnAssign)) and isinstance(
            item.value, ast.Call
        ):
            call = item.value
            if any(
                isinstance(arg, ast.Name) and arg.id == node.name for arg in call.args
            ):
                target = (
                    call.func.func if isinstance(call.func, ast.Call) else call.func
                )
                if isinstance(target, ast.Name) and target.id in names:
                    return True
                if isinstance(target, ast.Attribute) and target.attr == "task":
                    return True
        pending.extend(ast.iter_child_nodes(item))
    return False


def task_changes(collection: Collection, source_path: Path) -> dict[str, Change]:  # pylint: disable=too-many-locals
    """Return canonical task paths changed in the source file since HEAD.

    Only the task's own definition is compared; imported tasks and indirect
    changes to helpers or globals are outside this comparison.
    """
    path = source_path.resolve()
    try:
        current = ast.parse(path.read_bytes(), filename=str(path))
        previous = ast.parse(_head_source(path), filename=f"HEAD:{path.name}")
    except (OSError, SyntaxError, ValueError) as error:
        raise Exit(
            "Unable to compare task definitions with Git HEAD.", code=1
        ) from error
    old: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for node in _module_functions(previous):
        old.setdefault(node.name, []).append(node)
    current_nodes = list(_module_functions(current))
    occurrences: dict[str, int] = {}
    definitions = {}
    for node in current_nodes:
        occurrence = occurrences.get(node.name, 0)
        occurrences[node.name] = occurrence + 1
        line = min([node.lineno, *(d.lineno for d in node.decorator_list)])
        definitions[(node.name, line)] = (node, occurrence)
    changes: dict[str, Change] = {}
    for name in collection.task_names:
        body = inspect.unwrap(collection[name].body)
        code = getattr(body, "__code__", None)
        if code is None or Path(code.co_filename).resolve() != path:
            continue
        definition = definitions.get((body.__name__, code.co_firstlineno))
        if definition is None:
            continue
        node, occurrence = definition
        candidates = old.get(node.name, [])
        historical = candidates[occurrence] if occurrence < len(candidates) else None
        if historical is None or (
            _task_decorated(node, current) and not _task_decorated(historical, previous)
        ):
            changes[name] = "new"
        elif ast.dump(node) != ast.dump(historical):
            changes[name] = "updated"
    return changes


def filter_changed(
    collection: Collection, changes: dict[str, Change], prefix: str = ""
) -> Collection:
    """Copy the listing tree, retaining changed tasks, aliases and defaults."""
    filtered = Collection(
        collection.name or "", auto_dash_names=collection.auto_dash_names
    )
    for name, task in collection.tasks.items():
        if prefix + name in changes:
            filtered.add_task(
                task,
                name=name,
                aliases=tuple(collection.tasks.aliases_of(name)),
                default=False,
            )
    for name, child in collection.collections.items():
        selected = filter_changed(child, changes, prefix + name + ".")
        if selected:
            filtered.add_collection(selected, name=name)
            for alias in collection.collections.aliases_of(name):
                filtered.collections.alias(alias, to=name)
    filtered.__doc__ = collection.__doc__
    filtered.default = (
        collection.default
        if collection.default in filtered.tasks
        or collection.default in filtered.collections
        else None
    )
    return filtered
