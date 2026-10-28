# Invoke Toolkit

[![PyPI - Version](https://img.shields.io/pypi/v/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/invoke-toolkit.svg)](https://pypi.org/project/invoke-toolkit)

**Python tasks for humans and AI agents, built on [Invoke](https://www.pyinvoke.org/).**

Invoke Toolkit keeps Invoke's task functions, contexts, namespaces and task chaining, and adds typed arguments, Rich terminal output, shell completion, reusable plugins and portable PEP 723 scripts. Use it as a library to build project automation, then expose the same tasks to a person at a terminal or an agent invoking explicit commands.

[Documentation](https://d3f0.github.io/invoke-toolkit/) · [Quickstart](https://d3f0.github.io/invoke-toolkit/getting-started/quickstart/) · [Migrating from Invoke](https://d3f0.github.io/invoke-toolkit/getting-started/from-invoke/) · [Improvement history](https://d3f0.github.io/invoke-toolkit/reference/improvements/)

## Install and run your first task

Requires **Python 3.10+**; the library depends on **Invoke 3.0.3+** and **Rich 13+** ([compatibility change #114](https://github.com/D3f0/invoke-toolkit/pull/114)). With [uv](https://docs.astral.sh/uv/), install into a project:

```sh
uv add invoke-toolkit
```

Save this as `tasks.py`:

```python
from invoke_toolkit import Context, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Greet a person or an automation client."""
    print(f"Hello, {name}!")
```

Discover, inspect and execute it:

```sh
uv run intk --list
uv run intk --help hello
uv run intk hello --name toolkit
```

## For humans: a helpful terminal interface

- [Rich output and status](https://d3f0.github.io/invoke-toolkit/humans/rich-output/): styled messages, spinners, and a transient live panel showing the last three lines of subprocess output with `--show-command-output` ([#105](https://github.com/D3f0/invoke-toolkit/pull/105)). Disable animation when debugging ([#19](https://github.com/D3f0/invoke-toolkit/pull/19), [#25](https://github.com/D3f0/invoke-toolkit/pull/25)).
- [Completion](https://d3f0.github.io/invoke-toolkit/humans/completion/): install bash, zsh or fish support; complete typed choices, paths and configuration-aware callbacks ([#38](https://github.com/D3f0/invoke-toolkit/pull/38), [#41](https://github.com/D3f0/invoke-toolkit/pull/41), [#64](https://github.com/D3f0/invoke-toolkit/pull/64), [#101](https://github.com/D3f0/invoke-toolkit/pull/101), [#139](https://github.com/D3f0/invoke-toolkit/pull/139)).
- [Interactive selection](https://d3f0.github.io/invoke-toolkit/humans/interactive-selection/): fzf integration, with a simpler Rich numbered selector when fzf is unavailable ([#80](https://github.com/D3f0/invoke-toolkit/pull/80)).
- Close task names, aliases and namespaces are suggested after a typo; suggestions never execute a replacement command ([#140](https://github.com/D3f0/invoke-toolkit/pull/140)).

[Start with the human workflow](https://d3f0.github.io/invoke-toolkit/humans/).

## PEP 723: one portable task file

Put dependency metadata and tasks in the same Python file. uv provides the environment; Toolkit's `script()` turns the file into an Invoke-style command interface. This is the bridge between an operator's local workflow and an agent's repeatable invocation.

Save as `portable_tasks.py`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["invoke-toolkit"]
# ///
from invoke_toolkit import Context, script, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Greet from a standalone task file."""
    print(f"Hello, {name}!")


if __name__ == "__main__":
    script()
```

```sh
uv run --script portable_tasks.py hello --name PEP723
uv run --script portable_tasks.py --list --list-format json
```

With inline metadata, **uv ignores the surrounding project's dependencies**: declare everything the script imports. Toolkit still loads project configuration from the **current working directory**, not necessarily the script's directory ([#104](https://github.com/D3f0/invoke-toolkit/pull/104)); use `script(config_prefix="myapp")` for a custom configuration prefix ([#11](https://github.com/D3f0/invoke-toolkit/pull/11)).

For a Git-managed task file, `--list-changed` compares the current task definitions with `HEAD`, including staged and unstaged edits. New repositories without commits count all tasks as new. Imported tasks and indirect helper/global changes are excluded; this is not a dependency-impact analysis ([#146](https://github.com/D3f0/invoke-toolkit/pull/146)).

[Read the complete PEP 723 guide](https://d3f0.github.io/invoke-toolkit/pep723/) for configuration, dependency locking, import behavior and changed-task discovery.

## For AI agents: discover, inspect, execute

```sh
uv run intk --list --list-format json
uv run intk --help hello
uv run intk --disable-status hello --name agent
```

JSON is a **listing format**, not a universal output mode. Task authors own task results: emit explicit JSON to stdout and diagnostics to stderr when you need a machine-readable contract. Listing and help import Python modules and execute top-level code; Toolkit is **not a sandbox**.

[Agent workflow and output contracts](https://d3f0.github.io/invoke-toolkit/agents/) · [Task-authoring skill](https://github.com/D3f0/invoke-toolkit/blob/main/skills/invoke-toolkit-tasks/SKILL.md) ([#110](https://github.com/D3f0/invoke-toolkit/pull/110))

## Build reusable automation

Use the canonical library guides for the full APIs and boundaries:

| Need | Guide |
| --- | --- |
| Enum, Literal, Annotated and path arguments | [Typed arguments](https://d3f0.github.io/invoke-toolkit/guides/typed-arguments/) |
| Project, `local_tasks.py` and reusable namespaces | [Collections](https://d3f0.github.io/invoke-toolkit/guides/collections/) |
| Entry-point discovery and persistent `uv tool` plugin management | [Plugins](https://d3f0.github.io/invoke-toolkit/guides/plugins/) |
| Config files, CLI editing and typed schemas | [Configuration](https://d3f0.github.io/invoke-toolkit/guides/configuration/) |
| Dynamic defaults, URI resolvers and managed temporary files | [Fields](https://d3f0.github.io/invoke-toolkit/guides/fields/) |
| Optional task-result and completion caches | [Caching](https://d3f0.github.io/invoke-toolkit/guides/caching/) |
| Awaited commands and explicit concurrency | [Async tasks](https://d3f0.github.io/invoke-toolkit/guides/async/) |
| Subprocesses, redaction and process titles | [Execution](https://d3f0.github.io/invoke-toolkit/guides/execution/) |
| Reusable package templates | [Packages](https://d3f0.github.io/invoke-toolkit/guides/packages/) |

Optional packages are available as extras: `invoke-toolkit[cache]` for diskcache, `invoke-toolkit[copier]` or `invoke-toolkit[templating]` for package creation. Async task graphs remain sequential unless task code explicitly requests concurrency; the native async subprocess path is buffered and noninteractive, without PTY, watchers or sudo support.

Task and completion caches authenticate serialized values with HMAC-SHA256
before deserialization. The owner-only signing key lives under
`platformdirs.user_data_dir("invoke-toolkit")/cache-signing/cache.key`, outside
the cache directory. Unsigned legacy entries and tampered entries are cache
misses and are recomputed. Losing the key invalidates existing entries; if its
permissions or ownership are unsafe, caching is disabled rather than reading
unsigned data. New entries are stored inline in SQLite. Legacy DiskCache spill
files are not read or deleted automatically, because their filenames are
unauthenticated. See the [caching guide](https://d3f0.github.io/invoke-toolkit/guides/caching/).

These docs describe current `main`. A previously installed PyPI release may not include every recently merged improvement; see [installation options](https://d3f0.github.io/invoke-toolkit/getting-started/installation/) and the [complete PR map](https://d3f0.github.io/invoke-toolkit/reference/improvements/).

## Development

See [CONTRIBUTING.md](https://github.com/D3f0/invoke-toolkit/blob/main/CONTRIBUTING.md) for the uv environment, checks and Zensical documentation workflow. Runtime Python support remains 3.10+; the documentation toolchain requires Python 3.11+.

```sh
uv sync --group dev
uvx --with pre-commit-uv pre-commit install
```

## License

`invoke-toolkit` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license. See [LICENSE.txt](https://github.com/D3f0/invoke-toolkit/blob/main/LICENSE.txt).
