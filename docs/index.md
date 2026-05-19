# Welcome to Invoke Toolkit documentation

[![PyPI - Package Version](https://img.shields.io/pypi/v/invoke-toolkit)](https://pypi.org/project/invoke-toolkit/)

!!! warning
    This software is in early development. Expect API breakages until version `0.1.x` is
    released.

!!! tip
    `invoke-toolkit` extends [`invoke`](https://docs.pyinvoke.org/en/stable/) classes and functions prepending `ToolkitXXX`
    for each extended class.

    For compatibility, when you do `from invoke_toolkit import task, Context` the names are preserved.

Invoke Toolkit is a set of opinionated extensions to the popular [Python invoke library](https://pyinvoke.org)
that allow to create easy to use automation focuses scripts, with the ability to share them in different ways (packages, repos, etc).

It takes advantage of some recent developments in the Python ecosystem such as [`inline scripting`](https://peps.python.org/pep-0723/),
the [`rich`](https://rich.readthedocs.io/en/stable/introduction.html) and [`uv`](https://github.com/astral-sh/uv) package manager.


Among its core features it extends the `Context` class with status updates

??? example "Context attributes like `ctx.status()` and `ctx.print` using rich"

    ```python
    @task()
    def long_task(ctx: Context):
        with ctx.status("Doing something slow"):
            ctx.run("sleep 1")
    ```

* Renames the `inv`/`invoke` to `it`/`invoke-toolkit`, reads the same `tasks.py`.
* Replaces `print()` with `rich`'s Console print (internal logging uses `rich` logger): `it -d`.
* Command echo defaults to `stderr` (`it -e`)

??? example "Built in collections to manage *plugins*"

    ```bash
    it -xl
    ```


## Installation

The recommended way to use `invoke-toolkit` is through `uv` package manager:

```bash
uv tool install invoke-toolkit
```

### Ad-hoc run with `uvx`/`pipx`

With `uvx` or `uv tool run`
```bash
uvx invoke-toolkit
```

With `pipx`
```bash
pipx run invoke-toolkit
```

## Simple task example

```python
from invoke_toolkit import task, Context

@task()
def build(ctx: Context):
    ctx.run("uv run zensical build")
```

## Built in collections
