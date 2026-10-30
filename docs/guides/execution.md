# Execution, redaction and process titles

Task chaining, contexts, subprocess Results and sudo originate in [Invoke](https://docs.pyinvoke.org/en/latest/api/context.html). Toolkit adds Rich output, selected output redaction, process titles, async dispatch and fixes for POSIX terminal input. For presentation APIs, see [Rich output](../humans/rich-output.md); for async restrictions, see [asynchronous tasks](async.md).

## Shell strings and argument lists

`ctx.run(command, **kwargs)` executes a **shell string**, not an argv list. Never concatenate untrusted parameter values or `ctx.remainder` directly into that string. `remainder` is inherited Invoke text after `--`, not pre-parsed safe arguments or a Toolkit validation feature.

For a command that accepts discrete arguments, use Python's `subprocess.run` with a list and no shell. This complete `tasks.py` uses the current Python executable and passes the input as data:

```python
import subprocess
import sys

from invoke_toolkit import Context, task


@task
def echo_argument(ctx: Context, text: str = "hello world") -> None:
    """Pass data as one argument, without shell parsing."""
    result = subprocess.run(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", text],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    print(result.stdout, end="")
```

```bash
intk echo-argument --text 'hello; this is one argument'
```

Run after [installation](../getting-started/installation.md). `capture_output=True` here is ordinary Python subprocess behavior and bypasses Toolkit's runner. For async argument-list execution, use `asyncio.create_subprocess_exec()`.

When you deliberately need the Toolkit shell runner, quote **every dynamic argument** for the actual shell. This complete alternative uses POSIX `shlex.join` and a fixed Python program:

```python
import shlex
import sys
from typing import cast

from invoke import Result
from invoke_toolkit import Context, task


@task
def echo_argument(ctx: Context, text: str = "hello world") -> None:
    command = shlex.join(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", text]
    )
    result = cast(Result, ctx.run(command, hide=True, in_stream=False, timeout=5))
    print(result.stdout, end="")
```

Quoting prevents shell interpretation, not leakage through command arguments, command echo or process listings. `shlex.join` is for POSIX shells, not a portable Windows shell encoder. Validate application arguments separately, especially options/paths accepted by the target command.

Toolkit tracks Invoke 3's `ctx.remainder` in its call/context classes ([#114](https://github.com/D3f0/invoke-toolkit/pull/114)); forwarding it is still your task's policy decision.

## Output redaction is not secret isolation

`ctx.redact(streams, patterns=None)` matches **environment variable names** with regex/fnmatch-style patterns and replaces their nonempty values in selected Toolkit output. `streams` is `"out"`, `"err"`, `"out,err"`, or a dictionary such as `{"out": ["DOCS_TOKEN"], "err": ["DOCS_TOKEN"]}`. The default for a string stream selector is all environment names (`["*"]`); explicitly select the smallest useful pattern set.

This example uses a harmless sample value, a constant subprocess command and the synchronous Toolkit runner:

```python
import os

from invoke_toolkit import Context, task


@task
def demonstrate_redaction(ctx: Context) -> None:
    """Demonstrate selected output filtering with non-sensitive sample data."""
    os.environ["DOCS_TOKEN"] = "documentation-sample-value"
    with ctx.redact("out,err", patterns=["DOCS_TOKEN"]):
        ctx.print(os.environ["DOCS_TOKEN"])
        ctx.run('printf "%s\\n" "$DOCS_TOKEN"', in_stream=False)
```

```bash
intk demonstrate-redaction
```

The value is sampled from the environment when the console's patterns are configured. Each default-runner invocation snapshots those values and substitutions. Its stdout/stderr filters retain possible secret prefixes across writes and flushes. Writes and redaction state are serialized when stdout and stdin echo share an output stream; pending nonsecret text drains only after all writers finish. This also protects verbose status capture and Invoke's `ctx.run(..., asynchronous=True)` path. Ordinary prompts are emitted immediately unless their suffix might be part of a secret; such a suffix waits for more output or final drainage. Switching runners can bypass filtering. Important limitations:

- Raw captured `Result.stdout`/`.stderr`, arbitrary `print`, files, logging frameworks, custom Rich renderables, command echo and process arguments are not generally protected by the redaction contract.
- Native async subprocess output (`ctx.run_async()` or `ctx.run()` inside an async task) bypasses the redacting runner. Use `hide=True` and avoid rendering secrets, rather than assuming async parity.
- Replacement matches literal displayed values, not structured secrets. Transformed or encoded values, secrets split across different streams, and separate `ctx.print()` calls can escape matching.
- Environment secrets still exist in the process/environment and may be visible to other processes. Managed [Field files](fields.md#scalar-text-versus-managed-path-files) are also real local files.
- Redaction initialization no longer logs secret values, but debug output can still disclose other sensitive configuration or command data. Do not enable debug with secrets present.
- Console state is shared across contexts in a process. The current redaction context manager does not reliably restore/clear patterns on first use or exceptional exit; do not depend on it as task-local secret cleanup or isolation.

The safest policy is not to print a secret at all. Use redaction as a best-effort presentation safeguard, never as a reason to send credentials on a command line or approve untrusted task modules.

Origins: redaction implementation [#30](https://github.com/D3f0/invoke-toolkit/pull/30). [#22](https://github.com/D3f0/invoke-toolkit/pull/22) is an autoprint regression test, not a separate security feature.

## Identify long-running work with process titles

Use `@task(proctitle="...")` for a task-wide title and `ctx.proctitle(title)` for one section. Both restore the original process title on exit, including exceptions. If `TMUX` is set, they also rename the tmux window and restore its previous name when that name was obtained.

```python
import time

from invoke_toolkit import Context, task


@task(proctitle="invoke-toolkit documentation example")
def wait(ctx: Context, seconds: float = 2.0) -> None:
    """Make a bounded, visible wait without changing project files."""
    with ctx.proctitle("invoke-toolkit documentation: waiting"):
        time.sleep(seconds)
    print("Wait complete")
```

```bash
intk wait --seconds 2
```

Titles are process-global labels, not per-coroutine isolation. Never put secret arguments in them. `tmux` must be available when running in a tmux environment. Inspect with your operating system's process viewer; exact visible title formatting is platform-dependent.

Origin: [#50](https://github.com/D3f0/invoke-toolkit/pull/50).

## Synchronous PTY and shell behavior

The synchronous default runner inherits Invoke's PTY/watchers/sudo model. Toolkit repairs macOS stdin probing, carriage-return forwarding and terminal restoration ([#137](https://github.com/D3f0/invoke-toolkit/pull/137), [#142](https://github.com/D3f0/invoke-toolkit/pull/142)). Actual interactive commands still require a foreground terminal and appropriate privileges; use Invoke's documented options rather than promising noninteractive PTY behavior.

`--init-shell` chooses the shell from `$SHELL` (or leaves the configured default when unset); it does not make shell input safe or mean all your interactive aliases/functions are loaded. `--disable-status` changes presentation, not command semantics. These flags originated in [#19](https://github.com/D3f0/invoke-toolkit/pull/19) and [#25](https://github.com/D3f0/invoke-toolkit/pull/25); their human-facing use belongs in [Rich output](../humans/rich-output.md).

For REPL/standalone convenience, root `run()` and `sudo()` use `global_context()`, a lazily constructed singleton with stdin disabled in a non-TTY. Use the task's supplied `ctx` inside tasks so you keep loaded configuration and execution lifecycle; do not assume the global singleton has loaded your project's config. Origin: [#13](https://github.com/D3f0/invoke-toolkit/pull/13).
