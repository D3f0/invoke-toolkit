# Asynchronous tasks

Toolkit awaits coroutine task bodies and provides native asyncio subprocess execution. Invoke's pre/main/post task graph remains **sequential by default**; marking tasks `async` does not schedule sibling tasks concurrently.

Origins: [#121](https://github.com/D3f0/invoke-toolkit/pull/121), sync/async and hidden-output repairs [#127](https://github.com/D3f0/invoke-toolkit/pull/127).

## Await a subprocess

After [installation](../getting-started/installation.md), save this complete `tasks.py`. The fixed command uses a POSIX shell and disables interactive input:

```python
from invoke_toolkit import Context, task


@task
async def check(ctx: Context) -> None:
    """Await a noninteractive command and consume its captured output."""
    result = await ctx.run_async("printf 'async-ok\\n'", hide=True, timeout=5)
    print(result.stdout, end="")
```

```bash
intk check
```

Inside an async task dispatched by Toolkit, `await ctx.run(...)` also uses this native path when `asynchronous` is not requested. Its static return annotation is `Result | Awaitable[Result]`, so `ctx.run_async()` is clearer for code and type checkers. In synchronous tasks—even in an invocation graph containing async tasks—`ctx.run()` remains blocking. Invoke's `asynchronous=True` returns its own Promise; it is not the same API as a coroutine or `run_async()`.

The CLI selects async dispatch for an async task graph. In your own event loop, use `await ToolkitExecutor(...).execute_async(...)`; do not call `asyncio.run()` within an already-running loop. Direct Python calls to async-decorated tasks return an awaitable and should use explicit `ctx.run_async()` rather than relying on the executor's async-context marker.

## Explicit concurrency with gather

Use standard `asyncio.gather()` or Toolkit's scope for independent awaitables **inside** a task. This complete alternative `tasks.py` submits two noninteractive commands:

```python
from invoke_toolkit import Context, task


@task
async def compare(ctx: Context) -> None:
    """Run independent commands concurrently, then print in submission order."""
    async with ctx.gather() as gather:
        gather(ctx.run_async("printf 'first\\n'", hide=True))
        gather(ctx.run_async("printf 'second\\n'", hide=True))
    for result in gather.results:
        print(result.stdout, end="")
```

```bash
intk compare
```

`AsyncGatherScope`, imported from `invoke_toolkit.context.async_tools`, schedules each submitted awaitable immediately. Calling the scope returns a task handle; after successful exit, `.results` is a tuple in submission order. A failure or exceptional scope exit cancels unfinished work and awaits cancellation. It does not make shared resources, configuration or files race-free. Process-title and Rich console state are process-global; avoid conflicting mutation from gathered work.

## Ordering and mixed graphs

Parameterized pre/post tasks and Invoke deduplication still apply. A synchronous pre-task finishes before the following async task, and async pre/post tasks are awaited in order. Grouped entries are flattened, not parallelized. Use `call()` to supply values to dependencies; dependency ordering is inherited from Invoke, while coroutine awareness is Toolkit-specific.

Do not put blocking network/file/subprocess work directly into coroutine bodies if it needs to overlap. Prefer an async API or deliberately move suitable blocking work to a worker thread. Field factories/resolvers are synchronous callbacks and are not automatically made concurrent by an async task.

## Native subprocess limits

`run_async(command, **kwargs)` merges `config.run` options with supported keyword overrides and returns an upstream Invoke `Result`. It uses a shell, disabled stdin and `communicate()`:

- stdout/stderr are captured in memory and displayed **after completion**, unless hidden; this is not streaming output or the Rich live last-lines panel.
- `hide=True` suppresses terminal rendering but leaves raw `.stdout`/`.stderr` in the Result.
- `warn=True` returns failed results; otherwise nonzero exit raises `UnexpectedExit`.
- `timeout` overrides `config.timeouts.command`; timeout raises `CommandTimedOut`. Cancellation and timeout terminate the immediate child process. Do not assume an entire shell-created descendant process tree is killed.
- `pty=True`, stream watchers, `echo_stdin`, enabled/custom input streams, `asynchronous=True` and `disown=True` are rejected.
- Interactive commands, prompts and password responders are not supported on this path. `ctx.sudo()` is not an async API and is unsupported for async task execution; keep sudo workflows in synchronous tasks.
- The native path bypasses Toolkit's synchronous `NoStdoutRunner`, including its redacting output wrappers and live-status output capture. Do not assume [redaction](execution.md#output-redaction-is-not-secret-isolation) applies to async subprocess output or command echo.

For untrusted arguments, use `asyncio.create_subprocess_exec()` with an argument list or careful POSIX quoting rather than concatenating a shell command; see [execution safety](execution.md#shell-strings-and-argument-lists). Use the synchronous runner for actual PTY interaction; its terminal fixes are separate improvements ([#137](https://github.com/D3f0/invoke-toolkit/pull/137), [#142](https://github.com/D3f0/invoke-toolkit/pull/142)).

Async return values can use [task caching](caching.md#task-result-cache) with the same constraints as synchronous tasks. Cached coroutine results are final values, not reusable coroutine objects.
