# Python tasks for humans and AI agents

**Invoke Toolkit extends [Invoke](https://www.pyinvoke.org/) with a `rich`er terminal interface, 
extended terminal completion and plugin management.** 
It adapts the base library to be Python script PEP723 + uv shebang friendly, adding a new CLI entrypoint
called `inkt` that can auto-install a more comprehensive shell completion. You can still use invoke_toolkit
as invoke but most of the quality of life improvements are on the new modalities.


## Quickstart

1. Install [uv](https://docs.astral.sh/uv/) installed, 
2. Run `invoke-toolkit` as a tool:


```sh
uv tool run invoke-toolkit -x create.script --name tasks.py
```

Save this complete `tasks.py`:

```python
from invoke_toolkit import Context, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Greet a person or automation client."""
    print(f"Hello, {name}!")
```

```sh
uv run intk --list
uv run intk hello --name toolkit
```

[Installation choices](getting-started/installation.md) · [Complete quickstart](getting-started/quickstart.md) · [From Invoke](getting-started/from-invoke.md)

## For humans: discoverable terminal workflows

- **[Rich output and status](humans/rich-output.md):** styled messages and status spinners, with an optional live panel for the last three subprocess output lines ([#105](https://github.com/D3f0/invoke-toolkit/pull/105)).
- **[Shell completion](humans/completion.md):** bash, zsh and fish installation; typed choices, paths and callbacks using loaded configuration ([#64](https://github.com/D3f0/invoke-toolkit/pull/64), [#101](https://github.com/D3f0/invoke-toolkit/pull/101), [#139](https://github.com/D3f0/invoke-toolkit/pull/139)).
- **[Interactive selection](humans/interactive-selection.md):** fzf when available, a simpler Rich numbered selector otherwise ([#80](https://github.com/D3f0/invoke-toolkit/pull/80)).
- **Helpful typo errors:** close task names, aliases and nested namespaces are suggested without running a replacement task ([#140](https://github.com/D3f0/invoke-toolkit/pull/140)).

[Choose the human workflow](humans/index.md).

## PEP 723: the portable bridge

A task file can carry its own dependency metadata. [uv](https://docs.astral.sh/uv/guides/scripts/) creates the script environment, and Toolkit's `script()` exposes the tasks as a familiar command interface. Send the same file to an operator, use it in CI, or let an agent discover its commands.

Save this as `portable_tasks.py`:

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

uv's inline script environment **does not include the surrounding project's dependencies**. Toolkit project configuration is a separate concern: `script()` loads it from the current working directory ([#104](https://github.com/D3f0/invoke-toolkit/pull/104)). Dependency isolation is not a sandbox: imports and tasks still execute Python code with the caller's permissions.

In a Git-managed file, `--list-changed` shows new or updated definitions compared with `HEAD`, including staged and unstaged edits. New files and repositories without commits count as new; helpers, globals and imported tasks are outside the comparison ([#146](https://github.com/D3f0/invoke-toolkit/pull/146)).

[Read the PEP 723 guide](pep723/index.md) for runnable scripts, configuration, locking and Git-aware discovery.

## For AI agents: explicit command contracts

Discover with `--list --list-format json`, inspect each task's help, then run only the intended task with explicit arguments. Authors can reserve stdout for JSON results and stderr for diagnostics.

```sh
uv run intk --list --list-format json
uv run intk --help hello
uv run intk --disable-status hello --name agent
```

JSON discovery is not universal JSON output. Task code owns execution output, and help/listing import modules and execute their top-level statements. Toolkit does not provide an MCP server, a sandbox or permission enforcement.

[Agent workflow](agents/index.md) · [Existing task-authoring skill](https://github.com/D3f0/invoke-toolkit/blob/main/skills/invoke-toolkit-tasks/SKILL.md) ([#110](https://github.com/D3f0/invoke-toolkit/pull/110))

## Go deeper with the library

| Build with | Read |
| --- | --- |
| Enum, Literal, Annotated, path validation and completion | [Typed arguments](guides/typed-arguments.md) |
| Project tasks, local namespaces and reusable collections | [Collections](guides/collections.md) |
| Entry-point plugins and persistent uv tool plugin management | [Plugins](guides/plugins.md) |
| Configuration editing and attrs-based schemas | [Configuration](guides/configuration.md) |
| Dynamic defaults, URI text resolvers and temporary files | [Fields](guides/fields.md) |
| Task-result and completion caches | [Caching](guides/caching.md) |
| Async task functions and explicit concurrency | [Async](guides/async.md) |
| Subprocesses, output redaction and process titles | [Execution](guides/execution.md) |
| Package templates and provider packages | [Packages](guides/packages.md) |

[CLI reference](reference/cli.md) · [Public API reference](reference/api.md) · [Troubleshooting](reference/troubleshooting.md) · [Complete merged-PR improvement map](reference/improvements.md)

These guides describe current `main`; a previously installed release may lag recently merged changes. Runtime support is Python 3.10+, Invoke 3.0.3+ and Rich 13+ ([#114](https://github.com/D3f0/invoke-toolkit/pull/114)). See [installation](getting-started/installation.md) for release and source-checkout workflows.
