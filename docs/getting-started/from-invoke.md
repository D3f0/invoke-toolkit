# From Invoke to Invoke Toolkit

Invoke Toolkit extends Invoke rather than replacing its task model. Existing task functions, namespaces, `ctx.run()`, `ctx.cd()`, pre/post tasks and `call()` remain familiar. Toolkit's additions are optional APIs you can adopt where they make your automation clearer.

## Install beside your task code

In your existing uv project:

```sh
uv add invoke-toolkit
uv run intk --list
```

Use `intk` explicitly. Toolkit also installs `inv` and `invoke-toolkit` entry points, while upstream Invoke installs its own `inv`; avoid assuming a bare `inv` comes from the package you intended.

The current library requires Python 3.10+ and Invoke 3.0.3+ ([PR #114](https://github.com/D3f0/invoke-toolkit/pull/114)). See [installation](installation.md) for released versus current-source workflows.

## Adopt Toolkit imports

This is a complete `tasks.py` that keeps Invoke-style chaining while adding Toolkit output:

```python
from invoke_toolkit import Collection, Context, call, task


@task
def hello(ctx: Context, name: str = "toolkit") -> None:
    """Print a greeting."""
    ctx.print(f"[green]Hello, {name}![/green]")


@task(pre=[call(hello, name="team")])
def welcome(ctx: Context) -> None:
    """Run the greeting before the welcome message."""
    ctx.print("[bold]Welcome to the project.[/bold]")


ns = Collection(hello, welcome)
```

```sh
uv run intk --list
uv run intk welcome
```

`Context` is Toolkit's context and `Collection` is Toolkit's collection. `@task` creates Toolkit tasks. The pre-task chain is inherited from Invoke; styled `ctx.print()` is a Toolkit output helper. Plain Invoke task objects can still be discovered by the Toolkit program, but Toolkit-specific decorator behavior requires the Toolkit decorator.

## Improvements over the basic Invoke interface

| Adopt when you need | Toolkit improvement | Guide and origin |
| --- | --- | --- |
| Validated argument choices | Enum and Literal conversion; Annotated help and completion | [Typed arguments](../guides/typed-arguments.md), [#38](https://github.com/D3f0/invoke-toolkit/pull/38), [#41](https://github.com/D3f0/invoke-toolkit/pull/41) |
| Operator-friendly progress | Rich status control and a transient subprocess-output panel | [Rich output](../humans/rich-output.md), [#19](https://github.com/D3f0/invoke-toolkit/pull/19), [#105](https://github.com/D3f0/invoke-toolkit/pull/105) |
| Tab-completed CLI arguments | Shell installers and loaded-config callbacks | [Completion](../humans/completion.md), [#64](https://github.com/D3f0/invoke-toolkit/pull/64), [#101](https://github.com/D3f0/invoke-toolkit/pull/101) |
| Personal or reusable tasks | `local_tasks.py`, package namespaces and entry-point collection plugins | [Collections](../guides/collections.md), [#21](https://github.com/D3f0/invoke-toolkit/pull/21), [#31](https://github.com/D3f0/invoke-toolkit/pull/31) |
| Editable configuration and typed structure | Built-in config commands and attrs-based schemas | [Configuration](../guides/configuration.md), [#52](https://github.com/D3f0/invoke-toolkit/pull/52), [#90](https://github.com/D3f0/invoke-toolkit/pull/90) |
| Context-sensitive defaults | `Field`, factories, URI text resolution and managed temporary files | [Fields](../guides/fields.md), [#128](https://github.com/D3f0/invoke-toolkit/pull/128) |
| Reused computed results | Optional diskcache-backed task-result caching | [Caching](../guides/caching.md), [#51](https://github.com/D3f0/invoke-toolkit/pull/51) |
| Coroutine task functions | Awaited task execution and explicit concurrent scopes | [Async](../guides/async.md), [#121](https://github.com/D3f0/invoke-toolkit/pull/121), [#127](https://github.com/D3f0/invoke-toolkit/pull/127) |
| Self-contained script invocation | `script()` plus PEP 723 dependency metadata | [PEP 723](../pep723/index.md), [#11](https://github.com/D3f0/invoke-toolkit/pull/11), [#104](https://github.com/D3f0/invoke-toolkit/pull/104) |
| Focused task discovery | Main/plugin listing scopes and Git-changed definitions | [CLI reference](../reference/cli.md), [#120](https://github.com/D3f0/invoke-toolkit/pull/120), [#146](https://github.com/D3f0/invoke-toolkit/pull/146) |

## Review behavioral boundaries during migration

- **Discovery imports code.** Listing, help and completion load task modules, so top-level Python statements still run. Move execution-only work inside tasks. Deferred `Field` defaults do not make the entire module safe to import.
- **Output is not universally structured.** `--list --list-format json` formats discovery only. Task return values printed with `autoprint=True` are not automatically JSON serialized. See [agent contracts](../agents/index.md).
- **Local discovery has a namespace.** `local_tasks.py` is added under `local`; a main task or alias named `local` wins and skips the auxiliary file ([#133](https://github.com/D3f0/invoke-toolkit/pull/133)).
- **Async does not mean parallel.** The task graph is sequential by default; explicit task code requests concurrency. Native async subprocess output is buffered, and PTY, watchers and sudo are unsupported there.
- **Redaction is output handling, not isolation.** Selected rendered output can be redacted; that does not hide process arguments, environment contents or every possible leakage channel. See [execution](../guides/execution.md).
- **Portable dependency and config roots differ.** uv metadata defines the script environment and ignores surrounding project dependencies; `script()` loads Toolkit project config from the caller's current working directory.

## Next steps

Pick the [human workflow](../humans/index.md), package a [portable task file](../pep723/index.md), or define an [agent-facing output contract](../agents/index.md). The [complete PR map](../reference/improvements.md) separates Toolkit improvements from maintenance and inherited Invoke behavior.
