# PEP 723: portable task files

[PEP 723 inline script metadata](https://peps.python.org/pep-0723/) lets a Python file declare its dependencies and Python requirement. [uv](https://docs.astral.sh/uv/guides/scripts/) provides the execution environment; Invoke Toolkit's `script()` exposes decorated tasks through an Invoke-style command interface.

This is the bridge between [human terminal workflows](../humans/index.md) and [agent command contracts](../agents/index.md): both audiences can invoke the same file, inspect its help and discover its task names.

## A complete runnable script

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then save this file as `portable_tasks.py`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["invoke-toolkit"]
# ///
import json

from invoke_toolkit import Context, script, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Greet from a standalone task file."""
    print(f"Hello, {name}!")


@task
def report(ctx: Context, count: int = 3) -> None:
    """Emit an explicit JSON result, with no Rich output on stdout."""
    print(json.dumps({"status": "ok", "count": count}, sort_keys=True))


@task
def show_config(ctx: Context) -> None:
    """Print the greeting configured in the caller's working directory."""
    print(ctx.get_config_value("demo.greeting", default="Hello from defaults"))


if __name__ == "__main__":
    script()
```

Discover, inspect and run:

```sh
uv run --script portable_tasks.py --list
uv run --script portable_tasks.py --help hello
uv run --script portable_tasks.py hello --name PEP723
uv run --script portable_tasks.py report --count 5
uv run --script portable_tasks.py --list --list-format json
```

The dependency name installs the available release from the configured package index. These docs describe current `main`; when using a previously published release, recently merged features may not yet be available. See [installation](../getting-started/installation.md) for current-source execution and [improvement history](../reference/improvements.md) for origins.

On POSIX systems supporting `env -S`, the shebang also permits:

```sh
chmod +x portable_tasks.py
./portable_tasks.py hello --name teammate
```

uv must be on `PATH`. PEP 723 does not create a native binary or bundle a Python interpreter into the file.

## Keep the dependency contract in the file

The metadata block contains TOML in comments. `dependencies` is required, even when empty, and `requires-python` lets uv choose a compatible interpreter. uv can manage Python downloads according to its own configuration.

When inline metadata is present, **uv ignores the surrounding project's dependencies**. The project's `uv.lock` is not the script's dependency lock. Declare all packages imported by the script, not only Toolkit. Add dependencies using uv's metadata-aware command:

```sh
uv add --script portable_tasks.py 'invoke-toolkit[cache]'
```

Imports from your local project are not automatically packaged or installed merely because the script runs next to `pyproject.toml`. If your automation fundamentally depends on the installed project, a project environment with `uv run intk` may be the clearer choice; see [installation](../getting-started/installation.md).

### Lock the script's dependencies

For a repeatable dependency selection:

```sh
uv lock --script portable_tasks.py
uv run --locked --script portable_tasks.py report --count 5
```

uv creates `portable_tasks.py.lock` adjacent to the file. Keep it with the script when reproducibility matters. `--locked` requires the lockfile to remain consistent with the declared metadata rather than silently updating it. These are uv features, not Toolkit's task-result [cache](../guides/caching.md).

## What `script()` does

`script(argv=None, exit=True, config_prefix=None)` inspects its caller's locals and builds a collection from `Task` objects in that scope. Put it **after task definitions**, and use the `if __name__ == "__main__"` guard shown above when the file should also be importable without starting CLI execution.

It supports standard help, listing and task invocation through Toolkit's program. For ordinary project discovery, use `intk`; `script()` constructs its namespace from the calling file and is not a substitute for the project's loader/entry-point merge workflow.

The default uses process arguments and exits through the program's normal CLI behavior. The `exit=False` option is primarily useful for embedding/testing and is not a structured exception-reporting API. See [API reference](../reference/api.md).

### Import-time code still executes

Toolkit detects collection parsing and skips an unguarded `script()` call to avoid double CLI execution when a task file is loaded through its normal loader ([PR #17](https://github.com/D3f0/invoke-toolkit/pull/17)). This is narrow protection for that entrypoint—not general import safety.

All other top-level statements execute when Python imports the task module, including during help, listing and completion. Keep network requests, subprocess calls, prompts, file writes and secret resolution in task bodies or deferred [Field](../guides/fields.md) factories/resolvers. Field callbacks are deferred during discovery, but unrelated import code is not.

Toolkit also exposes top-level `run()`, `sudo()` and `global_context()` convenience APIs ([PR #13](https://github.com/D3f0/invoke-toolkit/pull/13)). Calling them at module level still performs work during import; inside tasks, prefer the provided `ctx`, which carries the execution configuration.

## Project configuration follows the current directory

Dependency isolation and configuration discovery are different layers. `script()` loads Toolkit project configuration from the **current working directory** ([PR #104](https://github.com/D3f0/invoke-toolkit/pull/104)), not automatically from the directory containing the script.

Place `invoke.yaml` in the directory from which you run the example:

```yaml
demo:
  greeting: Hello from invoke.yaml
```

```sh
uv run --script portable_tasks.py show-config
```

If you invoke the same script by an absolute or relative path from another directory, that other directory is the project-configuration location. Choose the working directory deliberately in shell scripts, CI and agent executions. The normal `intk` loader instead derives its project config location from the resolved task/search directory; see [configuration](../guides/configuration.md).

### Use a custom configuration prefix

[PR #11](https://github.com/D3f0/invoke-toolkit/pull/11) adds `config_prefix`. This complete alternative file, `custom_tasks.py`, looks for configuration using the `myapp` prefix:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["invoke-toolkit"]
# ///
from invoke_toolkit import Context, script, task


@task
def greeting(ctx: Context) -> None:
    """Print a value from custom-prefix configuration."""
    print(ctx.get_config_value("demo.greeting", default="Hello from defaults"))


if __name__ == "__main__":
    script(config_prefix="myapp")
```

Save `myapp.yaml` in the invocation directory:

```yaml
demo:
  greeting: Hello from myapp.yaml
```

```sh
uv run --script custom_tasks.py greeting
```

This changes the configuration prefix, including the names used by Invoke's file/environment configuration mechanisms. It does not change the uv dependency environment or choose a script-relative config directory. Default `script()` uses the normal `invoke` prefix. See [configuration](../guides/configuration.md) for the supported file formats and precedence.

## List changed task definitions

[PR #146](https://github.com/D3f0/invoke-toolkit/pull/146) adds `--list-changed` for a Git-managed source file, including PEP 723 scripts:

```sh
uv run --script portable_tasks.py --list-changed
uv run --script portable_tasks.py --list-changed --list-format json
```

With the same file available to the project loader as `tasks.py`, this also works:

```sh
intk --list-changed
intk --list --list-format json
```

`--list-changed` is itself a listing trigger. For **normal** JSON discovery use `--list --list-format json`; `--list-format json` alone is not a request to list tasks.

### The comparison boundary

- The loaded file's current task definitions are compared with **Git `HEAD`**, so staged and unstaged edits are included together. It is not an index-only or latest-commit-diff view.
- Bodies, signatures, decorators and docstrings count. Comments, formatting and line-number shifts do not.
- A file absent from `HEAD` counts all its tasks as new. A Git repository with **no commits** also counts them as new.
- Promoting a helper to a decorated task counts as new. Changing an existing task's explicit decorator name counts as an update to that definition.
- Imported tasks and indirect changes through helpers or globals are excluded. This is not call-graph analysis, dependency tracking or proof that other tasks are unaffected.
- Historical source is parsed, **not executed**. Current task modules are still imported normally, so current top-level side effects remain possible.
- The repository is resolved from the task source file, not the invocation's current directory. That is distinct from script project-configuration discovery.

Normal flat/nested listings highlight new tasks in green and updated tasks in yellow when Rich enables terminal colors; `NO_COLOR` is respected. JSON keeps Invoke's listing schema and does not add change-status fields. With no changes, changed listing succeeds with an empty JSON task list or a human-readable message. Without Git, outside a Git repository, or without an available task source, changed listing reports an error; normal listing can still work without highlights.

Changed listing can be combined with a namespace scope or main/plugin filters ([PR #120](https://github.com/D3f0/invoke-toolkit/pull/120)); consult the [CLI reference](../reference/cli.md) for exact combinations. A scoped list is discovery, not permission enforcement.

## Safety and next steps

A script environment is dependency isolation, **not a sandbox**. uv can install and execute third-party package code, and tasks run with the caller's permissions. Review the file, metadata and dependency provenance before execution. Do not regard help, listing or changed-task discovery as safe execution of untrusted Python.

- [For humans](../humans/index.md): terminal status, completion and selection.
- [For agents](../agents/index.md): explicit discovery and task-output contracts.
- [Typed arguments](../guides/typed-arguments.md), [configuration](../guides/configuration.md) and [Fields](../guides/fields.md): author reliable task interfaces.
- [CLI](../reference/cli.md), [API](../reference/api.md) and [troubleshooting](../reference/troubleshooting.md): exact flags, signatures and failure boundaries.
