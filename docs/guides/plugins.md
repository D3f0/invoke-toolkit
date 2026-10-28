# Installed collection plugins

Toolkit discovers task collections from Python package entry points. A plugin is reusable automation installed in the **same Python environment** as the `intk` that runs it. Discovery does not install packages, create environments or synchronize dependencies.

## Publish a collection entry point

This minimal package has three files. Put them in a new directory `invoke-toolkit-demo`, then run the installation commands from that directory. [Package generation](packages.md) can create the equivalent structure for you.

`pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "invoke-toolkit-demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["invoke-toolkit"]

[project.entry-points."invoke_toolkit.collection"]
"invoke-toolkit-demo" = "invoke_toolkit_demo:collection"

[tool.hatch.build.targets.wheel]
packages = ["src/invoke_toolkit_demo"]
```

`src/invoke_toolkit_demo/tasks.py`:

```python
from invoke_toolkit import Context, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Greet someone from an installed plugin."""
    print(f"Hello, {name}!")
```

`src/invoke_toolkit_demo/__init__.py`:

```python
from invoke_toolkit import Collection

collection = Collection("demo")
collection.add_flat_tasks_from_namespace("invoke_toolkit_demo")
```

With [uv](https://docs.astral.sh/uv/) installed:

```bash
uv venv
uv pip install --python .venv/bin/python -e .
.venv/bin/intk --list
.venv/bin/intk demo.hello --name reader
```

These commands use a POSIX environment path. Installing in an unrelated global, project or tool environment does not make this plugin visible here.

The actual entry-point group is **`invoke_toolkit.collection`**, not `invoke.collections`. Point directly to a Toolkit `Collection` instance for predictable loading; the loader also supports modules with collections/tasks. Entry-point names beginning with `invoke-toolkit-` are shortened, so the example is exposed as `demo`, not `invoke-toolkit-demo`. The distribution name alone does not decide the CLI namespace.

Origins: entry-point and flat discovery [#31](https://github.com/D3f0/invoke-toolkit/pull/31), short names [#33](https://github.com/D3f0/invoke-toolkit/pull/33).

## Discovery and namespace boundaries

With a primary `tasks.py`, installed plugin collections are merged as root subcollections. Without a task file, installed collections can supply the collection themselves. Use explicit, unique plugin namespace names: duplicate shortened plugin names warn and keep only the first entry point encountered; this is not a stable priority system. Do not reuse a project subcollection name for a plugin because merging follows Invoke's collection behavior rather than guaranteeing project precedence.

```bash
.venv/bin/intk --list-tasks
.venv/bin/intk --list-plugins
.venv/bin/intk --list --list-format json
```

`--list-tasks` retains primary and non-plugin subcollections; `--list-plugins` retains installed plugin collections. Both respect listing format/depth. If both scope flags are supplied, the task scope wins. JSON discovery still needs a listing flag; `--list-format json` alone does not request a list. See the [agent guide](../agents/index.md) and [CLI reference](../reference/cli.md).

Discovery imports Python code, including during listing, help and completion. Install only packages you trust and avoid import-time subprocesses or network calls. Field factories/resolvers are deferred, but module-level code is not. To reduce completion latency only, set `INVOKE_COMPLETION_DISABLE_PLUGINS=1`; normal execution and listing still discover installed plugins.

Origins: scoped lists [#120](https://github.com/D3f0/invoke-toolkit/pull/120), completion opt-out [#144](https://github.com/D3f0/invoke-toolkit/pull/144).

## Persistent uv tool lifecycle

The built-in `plugin` collection manages plugins installed alongside a **persistent `uv tool install`** of Invoke Toolkit. Run it with that tool's `intk`, not `.venv/bin/intk`, `uvx`, `uv run` or another project executable. Ensure the uv tool executable directory is on `PATH` and no active virtual environment shadows it.

From the root of the complete plugin package above, link it to the persistent tool:

```bash
uv tool install invoke-toolkit
uv tool update-shell
intk -x plugin.list
intk -x plugin.link .
intk demo.hello
```

`uv tool update-shell` updates shell startup configuration; start a new shell if its PATH was not already configured. Do not unintentionally replace an existing tool installation just to try the example: use [project-environment installation](../getting-started/installation.md) when you do not want persistent changes.

| Task | Purpose |
| --- | --- |
| `intk -x plugin.list` | Inspect plugin distributions, entry points and known sources |
| `intk -x plugin.add .` | Add a static, non-editable copy of the package in the current directory |
| `intk -x plugin.link .` | Link the current local package as editable |
| `intk -x plugin.remove invoke-toolkit-demo` | Remove a directly installed plugin |
| `intk -x plugin.update invoke-toolkit-demo` | Update a named non-editable plugin |
| `intk -x plugin.update` | Update all non-editable plugins; report skipped editables |

The table shows alternatives, not a sequence to run on the same package. `add` also accepts a package requirement or URL. Editable plugin source changes are visible without reinstalling; dependency/metadata changes can still need installation. Names for remove/update may be distribution or entry-point names, and ambiguous matches are rejected. These mutations rebuild the persistent tool installation from its uv receipt while preserving replayable base/supplemental requirements, constraints, extras, revisions and editable sources. A missing or unreplayable receipt blocks mutation rather than guessing install arguments.

Lifecycle ownership is determined by distributions exposing `invoke_toolkit.collection` entry points, not all supplemental dependencies. Resolver-only Field packages are not collection plugins and are not managed by these commands. Do not use `uv tool upgrade invoke-toolkit` as a documented substitute for plugin receipt-aware mutations.

Origin: [#138](https://github.com/D3f0/invoke-toolkit/pull/138). For pipx, environment management remains manual (`pipx inject invoke-toolkit PACKAGE`, `pipx uninject invoke-toolkit PACKAGE`, `pipx upgrade-injected invoke-toolkit`). Check [pipx's commands](https://pipx.pypa.io/stable/docs/) before modifying an installation; Toolkit's lifecycle tasks are uv-specific.
