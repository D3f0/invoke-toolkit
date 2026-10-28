# Rich output and status

Toolkit adds Rich helpers to the task context without changing the basic Invoke task model. Choose the stream deliberately, and use live status for terminal feedback rather than as a durable log.

## Print to the appropriate stream

| Helper | Stream | Purpose |
| --- | --- | --- |
| `ctx.print(...)` | stdout | Rich-formatted task output |
| `ctx.print_err(...)` | stderr | Rich-formatted diagnostics |
| `ctx.console.print(...)` | stderr | Full Rich console API and renderables |
| `ctx.inspect(obj)` | stderr by default | Rich object inspection; `stream="out"` selects stdout |
| Python `print(...)` | stdout by default | Plain text, including explicitly serialized JSON |

`ctx.console` defaults to the error console, not the stdout console. This distinction matters when task stdout will be parsed. `ctx.rich_exit(message, exit_code=1)` logs the message through the error console and exits; it is not a JSON error formatter.

Save this as `tasks.py` in a project with Toolkit installed:

```python
from invoke_toolkit import Context, task
from rich.table import Table


@task
def report(ctx: Context) -> None:
    """Show a small human-readable report."""
    ctx.print("[bold green]Report ready[/bold green]")
    ctx.print_err("[dim]Two entries were inspected.[/dim]")
    table = Table("Task", "State")
    table.add_row("hello", "ready")
    table.add_row("report", "ready")
    ctx.console.print(table)
```

```sh
uv run intk report
```

Rich markup is for trusted formatting, not an output serialization format. For machine results use [explicit JSON output](../agents/index.md#own-the-task-output-contract). `autoprint=True` prints a returned string or `Path` as plain text and other values through Rich; returning a dict does not guarantee JSON ([PR #36](https://github.com/D3f0/invoke-toolkit/pull/36)).

## Use status for work in progress

The context's `status()` manages a Rich spinner. Update it through the yielded status object or `ctx.status_update()`; `ctx.status_stop()` stops the current display for debugging.

This complete example runs the current Python interpreter as a child process. Replace the previous `tasks.py` with:

```python
import shlex
import sys

from invoke_toolkit import Context, task


@task
def progress(ctx: Context) -> None:
    """Run a child process while displaying progress."""
    code = (
        "import time\n"
        "for number in range(1, 6):\n"
        "    print(f'step {number}', flush=True)\n"
        "    time.sleep(0.3)\n"
    )
    command = shlex.join([sys.executable, "-u", "-c", code])
    with ctx.status("Running five steps") as status:
        ctx.run(command, in_stream=False)
        status.update("Steps finished")
    ctx.print("[green]Finished.[/green]")
```

```sh
uv run intk progress
```

Nested `ctx.status()` blocks reuse and update the current status object rather than creating independent stacked displays. A status message is progress feedback; it does not itself validate that the underlying work succeeded.

## Show live subprocess output below the spinner

[PR #105](https://github.com/D3f0/invoke-toolkit/pull/105) adds the Toolkit improvement over a plain spinner: a Rich Live panel for the last **three** subprocess output lines.

Using the `progress` task above:

```sh
uv run intk --show-command-output progress
uv run intk -O progress
```

During an active status block the synchronous Toolkit runner feeds subprocess stdout and stderr lines into the panel. The display is **transient** and disappears when the status ends. The panel is not a complete captured log, persistent output file or universal streaming interface.

The live-panel runner path overrides `hide` so output can reach the panel, even for `ctx.run(..., hide=True)`. Do not use `hide=True` as a secrecy boundary in a verbose status block. Captured `Result.stdout` and `Result.stderr` remain separate from what you choose to print; see [execution](../guides/execution.md).

This example is synchronous. Native [async subprocess execution](../guides/async.md) is buffered and noninteractive; do not expect this synchronous live-panel behavior there.

## Disable animation for debugging

Status control was introduced in [PR #19](https://github.com/D3f0/invoke-toolkit/pull/19), with the `--ds` spelling and shell initialization support in [PR #25](https://github.com/D3f0/invoke-toolkit/pull/25).

```sh
uv run intk --disable-status progress
uv run intk --ds progress
```

Or set the default in `invoke.yaml`:

```yaml
disable_status: true
```

For one invocation in a POSIX shell:

```sh
INVOKE_DISABLE_STATUS=1 uv run intk progress
```

Disabling status removes animation but does **not** silence status entirely: the disabled implementation prints entry and exit messages. It also does not make arbitrary task output JSON. Use it around breakpoints, REPL work or noninteractive execution where live updates are distracting.

`--init-shell` sets the subprocess shell from `$SHELL` when provided. It does not install completion or promise to source your interactive shell startup files. Completion setup is covered separately in [completion](completion.md).

## Redaction and process titles

Output redaction for synchronous subprocess rendering is documented in [PR #30](https://github.com/D3f0/invoke-toolkit/pull/30). Process-title context and decorator APIs are documented in [PR #50](https://github.com/D3f0/invoke-toolkit/pull/50). Read the [execution guide](../guides/execution.md) for exact usage and limits: rendering redaction is not a sandbox, does not hide process arguments or every leakage channel, and should not be generalized to native async execution.

[Human workflow](index.md) · [Interactive selection](interactive-selection.md) · [CLI reference](../reference/cli.md) · [Troubleshooting](../reference/troubleshooting.md)
