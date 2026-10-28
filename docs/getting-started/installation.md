# Installation

Invoke Toolkit is both a Python library and a CLI. Choose an environment that contains the tasks' imports and any plugins you intend to discover.

## As a tool

```bash
uv tool install invoke-toolkit[full]
```




## Compatibility and release scope

The runtime requires **Python 3.10+**, **Invoke 3.0.3+** and **Rich 13+**. The Invoke 3 compatibility cutover is documented in [PR #114](https://github.com/D3f0/invoke-toolkit/pull/114). The documentation build toolchain separately needs Python 3.11+; it does not raise the library's runtime floor.

These pages describe the source on current `main`. A previously installed PyPI release may not contain all recently merged changes. Check your installation with:

```sh
intk --version
```

Use the [improvement history](../reference/improvements.md) to find the originating changes, and the source-checkout option below when you need current-main behavior.

## Add the library to a project

With [uv](https://docs.astral.sh/uv/) and an existing `pyproject.toml`:

```sh
uv add invoke-toolkit
uv run intk --version
```

For a new project, initialize it first:

```sh
uv init toolkit-demo
cd toolkit-demo
uv add invoke-toolkit
```

Or install in an activated virtual environment using pip:

```sh
python -m pip install invoke-toolkit
intk --version
```

The package exposes `intk`, `invoke-toolkit` and `inv`, all pointing at Toolkit's program. `intk` is used throughout these guides to avoid ambiguity with upstream Invoke installations. Be aware that both packages expose an `inv` command; which one your shell finds depends on the environment and `PATH`.

Continue with the [quickstart](quickstart.md).

## Install a persistent CLI tool

For a CLI on your `PATH` with its own environment:

```sh
uv tool install invoke-toolkit
intk --version
```

[pipx](https://pipx.pypa.io/) is another option:

```sh
pipx install invoke-toolkit
intk --version
```

A tool environment does **not** automatically contain your project's Python dependencies. If a task imports a project-specific package, install that dependency in the tool environment or run Toolkit inside the project instead.

Reusable plugins are discovered from the environment running Toolkit. Built-in `plugin.add`, `plugin.link`, `plugin.remove`, `plugin.list` and `plugin.update` lifecycle commands require a persistent **`uv tool install`** environment. They reject transient `uvx`, project `uv run` and other installers; entry-point discovery is a separate feature ([PR #138](https://github.com/D3f0/invoke-toolkit/pull/138)). See the [plugins guide](../guides/plugins.md).

## Use a portable script instead

You do not need to install a global CLI to run a PEP 723 task file:

```sh
uv run --script portable_tasks.py --list
```

Create `portable_tasks.py` using the complete example in the [PEP 723 guide](../pep723/index.md). uv reads the file's inline dependency metadata and prepares its environment. When that metadata is present, uv ignores the surrounding project's dependencies; declare all script imports in the metadata.

## Optional dependencies

| Extra | Purpose | Origin |
| --- | --- | --- |
| `cache` | Persistent task-result and completion caches using diskcache | [#51](https://github.com/D3f0/invoke-toolkit/pull/51), [#76](https://github.com/D3f0/invoke-toolkit/pull/76) |
| `copier` or `templating` | Copier-based package creation | [#8](https://github.com/D3f0/invoke-toolkit/pull/8), [#144](https://github.com/D3f0/invoke-toolkit/pull/144) |
| `debug` | Optional debugging packages | [Project metadata](https://github.com/D3f0/invoke-toolkit/blob/main/pyproject.toml) |
| `full` | Copier, diskcache and the debug packages | [Project metadata](https://github.com/D3f0/invoke-toolkit/blob/main/pyproject.toml) |

Quote extras in shells that interpret square brackets:

```sh
uv add 'invoke-toolkit[cache]'
```

For a persistent tool environment with both cache and templating support:

```sh
uv tool install 'invoke-toolkit[cache,copier]'
```

Without diskcache, decorated callbacks and tasks can execute but do not get persistent caching. See [caching](../guides/caching.md). fzf is an external executable, not a Python extra; [interactive selection](../humans/interactive-selection.md) describes its reduced Rich fallback.

## Work from current source

Clone a Git checkout so Git-derived version metadata is available:

```sh
git clone https://github.com/D3f0/invoke-toolkit.git
cd invoke-toolkit
uv sync
uv run intk --version
```

For source installed in a separate activated virtual environment, from the cloned repository:

```sh
python -m pip install -e .
intk --version
```

Source-checkout execution is useful for checking current-main documentation. It is not the persistent uv tool environment required by plugin lifecycle commands. See [CONTRIBUTING](https://github.com/D3f0/invoke-toolkit/blob/main/CONTRIBUTING.md) for the full development and documentation workflow.

## Next steps

- [Write your first task](quickstart.md).
- [Migrate an Invoke task collection](from-invoke.md).
- [Install shell completion](../humans/completion.md).
- [Choose a portable PEP 723 file](../pep723/index.md).
- [Troubleshoot environments and discovery](../reference/troubleshooting.md).
