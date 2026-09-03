# invoke-toolkit

A set of extensions for rich output, more options in collection/config discovery through `entry-points`.

This extends the Collection from Invoke so it can create automatically collections.

[![PyPI - Version](https://img.shields.io/pypi/v/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)

-----

## Table of Contents

- [invoke-toolkit](#invoke-toolkit)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Do I need this package](#do-i-need-this-package)
  - [Installation](#installation)
  - [Development](#development)
  - [License](#license)

## Features

- Task discovery by namespace for extendable/composable CLIs
- Discovery to *plain old* tasks.py (or any other name)
- Local tasks discovery from `local_tasks.py` in the current directory
- Integration with stand alone binaries for specific tasks
- **Task result caching** with TTL support via `diskcache` (optional)
- **Future** Download binaries

## Do I need this package

If you have...

- Used `invoke` for a while and...
- Have a large `tasks.py` that needs to be modularized
- Have a lot of copy/pasted code in multiple `tasks.py` across multiple repos.
- Have exceeded the approach of a repository cloned as `~/tasks/` with more .py files that you want to manage.
- Or you want to combine various tasks defined in multiple directories
- You want to create a zipped (shiv) redistribute script for container environments
  like Kubernetes based CI environments with only requiring the Python interpreter.

## Installation

```console
pip install invoke-toolkit
```

## Quick Start

### Using Local Tasks

Create a `local_tasks.py` file in your project directory with your tasks:

```python
from invoke_toolkit import task

@task()
def my_task(ctx):
    """Do something useful"""
    print("Hello from local tasks!")
```

Then run it with:

```console
intk local.my-task
```

Local tasks are automatically discovered and added to the `local` namespace, allowing you to keep project-specific tasks separate from your main task collection.

### Using Task Caching

Cache expensive task results with the `cache` parameter:

```python
from invoke_toolkit import task

# Simple caching (no expiration)
@task(cache=True)
def expensive_task(ctx, param: str) -> str:
    """Results are cached across invocations."""
    return do_expensive_computation(param)

# Caching with TTL (1 hour)
@task(cache={"ttl": 3600})
def cached_task(ctx, name: str) -> dict:
    """Results cached for 1 hour."""
    return fetch_data(name)

# Caching with ignored arguments
@task(cache={"ttl": 600, "ignore_args": ["verbose"]})
def cached_with_options(ctx, query: str, verbose: bool = False) -> list:
    """Cache key ignores verbose flag."""
    return search(query, verbose=verbose)
```

Cache features:
- Cache location is computed from git repository root + platformdirs
- Debug logging (`-d` flag) shows cache hits/misses
- Graceful degradation when `diskcache` is not installed

To enable caching, install with the cache extra:

```console
pip install invoke-toolkit[cache]
```

## Dynamic task defaults

Use `Field` when an argument default must be computed from the final task
context or resolved from a URI. Explicit command-line values always take
precedence.

Bind a resolver once, then reuse the resulting callable for scalar and file
defaults. A local resolver always returns one string value per request. The
resolver receives every URI using that callback and scheme in one batch.

```python
from invoke_toolkit import Context, Field, FilePath, task


def resolve_bw(ctx: Context, requests: list) -> dict[str, str]:
    return {
        request.parameter: ctx.run("bw get password ...", hide=True).stdout.strip()
        for request in requests
    }


BitwardenField = Field(resolver=resolve_bw)
ExistingFile = FilePath(exists=True, dir_okay=False)


@task
def deploy(
    ctx: Context,
    password: str = BitwardenField(default="bw://PASSWORD_ID"),
    config: ExistingFile = BitwardenField(
        default="bw://CONFIG_ID", cleanup="task"
    ),
) -> None:
    ...
```

For `str` fields, the resolver string reaches the task unchanged. For `Path` or
`FilePath` fields, `Field.create_temporary_file()` writes that string to a
managed temporary file and passes its `Path` to the task. Override that method
in a `Field` subclass to control file creation; resolvers do not return paths.

For omitted arguments, lookup precedence is explicit CLI/Python/call value,
then `INVOKE_<PARAMETER>` environment value, then the resolved `ctx.config`
value, then the declared `Field` default or factory. URI values from config use
the same local or entry-point resolver dispatch as declared URI defaults.

`Field(default_factory=callback)` runs only if no higher-precedence value is
available. Factories and resolvers never run during help, listing, or shell
completion; `Path`/`FilePath` completion continues to work normally for
explicit values.

Temporary `Path` files from resolver-bound `Field` instances are owned by
invoke-toolkit. `cleanup="pipeline"` is the default and keeps the file through
expanded pre/main/post execution; `cleanup="task"` removes it when that task
returns. Cleanup runs after failures and cancellation.

Installed `invoke_toolkit.field_resolver` entry points remain supported for
compatibility but issue a warning recommending a task-local resolver. Generate a
resolver-only provider package with:

```console
intk -x create.package --provider op
```

Provider packages expose no task collection. Providers return text only; for
`Path` fields invoke-toolkit materializes and cleans the resulting temporary
file according to that Field's cleanup lifetime.

## uv tool plugins

This plugin-management workflow is currently for persistent `uv tool` installations only. Other package-manager plugin workflows are future work.

Install a plugin from Git or a local editable checkout with uv:

```console
uv tool install invoke-toolkit --with git+https://github.com/D3f0/invoke-toolkit-litellm
uv tool install invoke-toolkit --with-editable ./invoke-toolkit-litellm
```

When `intk` is running from a detectable uv tool environment, use the internal tasks to inspect and manage the installed `invoke-toolkit-*` plugins:

```console
intk -x plugin.list
intk -x plugin.add --package git+https://github.com/D3f0/invoke-toolkit-litellm
intk -x plugin.add --package invoke-toolkit-litellm --editable ./invoke-toolkit-litellm
intk -x plugin.remove invoke-toolkit-litellm
intk -x plugin.update
```

The `version` task identifies the uv-tool context and reports plugin versions when package metadata makes them available. For `uvx`, `uv run`, project virtual environments, or other package managers, plugin management is not claimed. Re-run `uv tool install` with the complete desired set of `--with` and `--with-editable` options when changing supplemental requirements.

> **Scope disclaimer:** pipx, Poetry, pip, and other package-manager plugin management options should come in a future release.

## Development

This project utilizes the `pre-commit` framework, make sure you run:

`pre-commit install`

With `uvx`:

`uvx --with pre-commit-uv pre-commit install`

## License

`invoke-toolkit` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
