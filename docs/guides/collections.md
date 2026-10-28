# Composing task collections

Invoke's `Collection` groups tasks, aliases, defaults and configuration. Toolkit adds package discovery and `local_tasks.py` loading. Installed entry-point collections are a separate [plugin mechanism](plugins.md).

## Built-in collections

Enable Toolkit's built-in collections with `-x` and list their tasks with `-l`:

```bash
uv run intk -xl
```

These include `config.show`, `config.get`, `config.set` and `config.unset`;
`create.add-shebang`, `create.package` and `create.script`; plugin lifecycle tasks;
and shell completion installers. Use [configuration](configuration.md),
[package generation](packages.md), [plugins](plugins.md) and
[completion](../humans/completion.md) for their arguments and boundaries.


## Explicit composition

For a small project, explicit imports and `add_collection()` are the most predictable choice. Save this complete example as `tasks.py` after [installation](../getting-started/installation.md):

```python
from invoke_toolkit import Collection, Context, task


@task
def report(ctx: Context) -> None:
    """Print a non-destructive build report."""
    print("Build configuration is ready")


@task(aliases=["check"])
def verify(ctx: Context) -> None:
    """Report that the task was reached."""
    print("Verification task selected")


build = Collection("build", report, verify)
ns = Collection()
ns.add_collection(build)
```

```bash
intk --list
intk build.report
intk build.check
```

Task-name normalization, aliases, default tasks and pre/post tasks are inherited from [Invoke collections](https://docs.pyinvoke.org/en/latest/concepts/namespaces.html). Toolkit warns and removes aliases that normalize to their own task name, rather than creating a recursive alias ([#116](https://github.com/D3f0/invoke-toolkit/pull/116)).

## Package discovery: flat or nested

Create a directory `automation` beside `tasks.py`. Its `__init__.py` can contain just a module docstring:

```python
"""Project automation modules."""
```

Save `automation/build.py`:

```python
from invoke_toolkit import Context, task


@task
def report(ctx: Context) -> None:
    """Describe the build module."""
    print("Build module")
```

Save `automation/checks.py`:

```python
from invoke_toolkit import Context, task


@task
def verify(ctx: Context) -> None:
    """Describe the checks module."""
    print("Checks module")
```

For a flat namespace, replace `tasks.py` with:

```python
from invoke_toolkit import Collection

ops = Collection("ops")
ops.add_flat_tasks_from_namespace("automation")
ns = Collection(ops)
```

```bash
intk ops.report
intk ops.verify
```

For module-qualified names, replace `tasks.py` with:

```python
from invoke_toolkit import Collection

ops = Collection("ops")
ops.add_collections_from_namespace("automation")
ns = Collection(ops)
```

```bash
intk ops.build.report
intk ops.checks.verify
```

The package must be importable in the executing Python environment. These helpers import discoverable submodules, not task definitions in the package's own `__init__.py`. Imports execute top-level code: discovery is not a sandbox. Keep modules import-safe, and use explicit composition when you need tight control over what loads.

Flattening removes a naming boundary. Give tasks unique names across flattened modules; Toolkit does not provide a conflict-resolution contract for duplicate task names there. Nested composition keeps module names distinct.

Origin: package composition [#8](https://github.com/D3f0/invoke-toolkit/pull/8), flat discovery [#31](https://github.com/D3f0/invoke-toolkit/pull/31).

## Module configuration with from_package

`Collection.from_package(package_path, into)` adds cleaned module subcollections into an **existing** collection and returns it. Unlike the two discovery helpers above, it collects module-level `config` dictionaries into root configuration keyed by the module name. It filters underscore-prefixed tasks and tasks imported from other modules. A module-level `config_schema` attribute referring to a `ConfigSchema` subclass is registered for validation; schema registration alone does not install schema defaults.

For the package above, a complete alternative `tasks.py` is:

```python
from invoke_toolkit import Collection

ns = Collection.from_package("automation", into=Collection())
```

```bash
intk build.report
intk checks.verify
```

Use [configuration schemas](configuration.md#attrs-and-cattrs-schemas) for structured values; choose `configure(schema=..., mapping=...)` when you want schema defaults applied explicitly. Origin: [#90](https://github.com/D3f0/invoke-toolkit/pull/90).

## Local developer tasks

Toolkit automatically looks for `local_tasks.py` alongside the primary task collection and exposes its public tasks under `local`. Keep project-wide automation in `tasks.py` and machine-specific convenience tasks in a gitignored `local_tasks.py`.

Save `local_tasks.py` next to one of the examples above:

```python
from pathlib import Path

from invoke_toolkit import Context, task


@task
def workspace(ctx: Context) -> None:
    """Print this developer's current directory."""
    print(Path.cwd())
```

```bash
intk local.workspace
```

Rules and boundaries:

- If the main collection has a task or alias named `local`, Toolkit warns and skips `local_tasks.py`; the main task/alias wins.
- Existing subcollections use Invoke's collection merge behavior. Do not rely on a pre-existing `local` subcollection being preserved when local-file discovery adds one.
- Local files in different directories use path-derived private module identities, so they do not share a single Python `local_tasks` module.
- A standalone local file can be used when no primary task file or installed plugin collection is found. When plugins alone supply the fallback collection, automatic local-file loading is not additionally performed.
- `load_local_tasks(search_path=None)` is available for explicit library use; its default is the current directory. `load_directory(directory)` only adds an import search path—it does not itself discover tasks. The `load_plugins()` method is currently a no-op; use namespace helpers or installed entry points instead.

Origins: [#21](https://github.com/D3f0/invoke-toolkit/pull/21), module identity repair [#123](https://github.com/D3f0/invoke-toolkit/pull/123), main namespace precedence [#133](https://github.com/D3f0/invoke-toolkit/pull/133).

Continue with [plugin packaging](packages.md) or [static API reference](../reference/api.md#collections).
