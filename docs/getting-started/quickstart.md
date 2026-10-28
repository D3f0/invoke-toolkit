# Your first task

Start with a Python project containing Invoke Toolkit ([installation](installation.md)). This example performs no subprocess or network work: it makes the task interface easy to see.

## Define a task

Save `tasks.py` in the project directory:

```python
from invoke_toolkit import Context, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Greet a person or an automation client."""
    print(f"Hello, {name}!")
```

## Discover, inspect, execute

From the directory containing the file:

```sh
uv run intk --list
uv run intk --help hello
uv run intk hello --name toolkit
```

`--list` shows available task names and descriptions. `--help hello` shows arguments for that task. The function's docstring is the task description, and its `name` parameter becomes `--name` with the declared default. Function names with underscores become dashed CLI names by default—standard Invoke behavior.

If you installed Toolkit directly in an activated environment, use `intk` instead of `uv run intk`. To begin task search in a different directory:

```sh
uv run intk --search-root . --list
```

## Add a typed choice

Replace `tasks.py` with this complete version:

```python
from typing import Annotated, Literal

from invoke_toolkit import Context, task


@task
def hello(
    ctx: Context,
    name: Annotated[str, "Who to greet"] = "toolkit",
    style: Literal["friendly", "formal"] = "friendly",
) -> None:
    """Greet with a validated style."""
    if style == "formal":
        print(f"Good day, {name}.")
    else:
        print(f"Hello, {name}!")
```

Toolkit validates the Literal value and includes the available choices in help ([PR #38](https://github.com/D3f0/invoke-toolkit/pull/38), [PR #41](https://github.com/D3f0/invoke-toolkit/pull/41)):

```sh
uv run intk --help hello
uv run intk hello --name toolkit --style friendly
uv run intk hello --name toolkit --style formal
```

`Annotated` keeps argument help next to the type. Enum choices, path conversion and completion markers are covered in [typed arguments](../guides/typed-arguments.md).

## Separate personal tasks

Keep the main `tasks.py` and add `local_tasks.py` alongside it:

```python
from invoke_toolkit import Context, task


@task
def where(ctx: Context) -> None:
    """Print the process's working directory."""
    from pathlib import Path

    print(Path.cwd())
```

Run:

```sh
uv run intk --list
uv run intk local.where
```

Toolkit loads these tasks under `local` ([PR #21](https://github.com/D3f0/invoke-toolkit/pull/21)). Loading is tied to the resolved task/search directory, not a global personal-tasks directory. A main task or alias named `local` takes precedence and causes `local_tasks.py` to be skipped with a warning ([PR #133](https://github.com/D3f0/invoke-toolkit/pull/133)). See [collections](../guides/collections.md) for discovery and namespace details.

## Let an agent discover the same interface

```sh
uv run intk --list --list-format json
uv run intk --disable-status hello --name agent --style formal
```

Both `--list` and `--list-format json` are needed for normal JSON discovery. The format flag alone does not request listing or convert task output to JSON. The `hello` task above deliberately emits a plain string; choose an explicit output contract for machine consumers in the [agent guide](../agents/index.md).

Help and listing import task modules and execute their top-level statements. Keep subprocesses, file writes, network requests and prompts inside task functions. Toolkit does not sandbox those imports.

## Choose your next workflow

- **At a terminal:** [Rich output](../humans/rich-output.md), [completion](../humans/completion.md), and [selection](../humans/interactive-selection.md).
- **One file with its own environment:** the central [PEP 723 guide](../pep723/index.md).
- **Existing Invoke code:** [migration](from-invoke.md).
- **Reusable task APIs:** [collections](../guides/collections.md), [configuration](../guides/configuration.md), and [Fields](../guides/fields.md).
- **Git-aware discovery:** [changed-task listing](../pep723/index.md#list-changed-task-definitions), introduced in [PR #146](https://github.com/D3f0/invoke-toolkit/pull/146).

For all command flags and API signatures, use the [CLI reference](../reference/cli.md) and [API reference](../reference/api.md).
