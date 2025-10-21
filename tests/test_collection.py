from pathlib import Path
import sys
from textwrap import dedent
import ast

from invoke_toolkit.collections import ToolkitCollection


def test_collection_load_submodules(monkeypatch, tmp_path: Path):
    """
    Creates some module in a temporary directory and tries to import from that location
    """
    ns = ToolkitCollection()
    code_module_for_tasks = dedent(
        """
    from invoke_toolkit import task
                  
    @task()
    def a_task(ctx):
        ...
    """
    )

    def create_module(folder: Path, name: str, code=code_module_for_tasks):
        file_to_write_to = folder / name
        file_to_write_to.write_text(code)
        return file_to_write_to

    ast.parse(code_module_for_tasks)
    # Simulate modules
    to_import_p: Path = tmp_path / "to_import"
    to_import_p.mkdir()
    tasks_p: Path = to_import_p / "tasks"
    tasks_p.mkdir()
    # Create the package manager for to_import.tasks (the __init__.py)
    (tasks_p / "__init__.py").write_text("")
    create_module(tasks_p, "mod1.py")
    create_module(tasks_p, "mod2.py")

    sys.path.append(str(tmp_path))

    ns.add_collections_from_namespace("to_import.tasks")

    found_collections = ns.collections
    assert set(found_collections.keys()) == {"mod1", "mod2"}
