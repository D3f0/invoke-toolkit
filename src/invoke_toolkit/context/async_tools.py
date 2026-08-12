"""Async execution helpers for :class:`ToolkitContext`."""

from __future__ import annotations

import asyncio
import asyncio.subprocess as async_subprocess
import contextvars
import os
import sys
from contextlib import contextmanager
from typing import Any, Awaitable, Iterator

from invoke.exceptions import CommandTimedOut, UnexpectedExit
from invoke.runners import Result, default_encoding, normalize_hide


_async_task_context: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "invoke_toolkit_async_task_context", default=False
)


@contextmanager
def async_task_context() -> Iterator[None]:
    """Mark synchronous context methods called from an async task."""
    token = _async_task_context.set(True)
    try:
        yield
    finally:
        _async_task_context.reset(token)


def in_async_task_context() -> bool:
    """Return whether the current execution is an invoke-toolkit async task."""
    return _async_task_context.get()


class AsyncGatherScope:
    """Schedule awaitables and await them together when the scope exits.

    Submitted awaitables start immediately. ``results`` contains their return
    values in submission order after a successful scope exit.
    """

    def __init__(self) -> None:
        self._tasks: list[asyncio.Future[Any]] = []
        self.results: tuple[Any, ...] = ()

    async def __aenter__(self) -> "AsyncGatherScope":
        return self

    def __call__(self, awaitable: Awaitable[Any]) -> asyncio.Future[Any]:
        """Schedule *awaitable* and return its task handle."""
        task = asyncio.ensure_future(awaitable)
        self._tasks.append(task)
        return task

    async def __aexit__(self, exc_type, exc_value, traceback) -> bool:
        if exc_type is not None:
            await self._cancel_remaining()
            return False

        try:
            self.results = tuple(await asyncio.gather(*self._tasks))
        except BaseException:
            await self._cancel_remaining()
            raise
        return False

    async def _cancel_remaining(self) -> None:
        pending = [task for task in self._tasks if not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


async def run_async_command(  # pylint: disable=too-many-branches,too-many-locals
    context: Any, command: str, **kwargs: Any
) -> Result:
    """Run a shell command without blocking the current event loop."""
    options = dict(context.config.run.items())
    for key, value in kwargs.items():
        if key not in options and key != "timeout":
            raise TypeError(f"run_async() got an unexpected keyword argument '{key}'")
        options[key] = value

    timeout = options.pop("timeout", context.config.timeouts.command)
    if options.get("asynchronous") or options.get("disown"):
        raise ValueError("run_async() cannot use asynchronous or disown")
    if options.get("pty"):
        raise ValueError("run_async() does not support pty=True")
    if options.get("watchers"):
        raise ValueError("run_async() does not support stream watchers")
    if options.get("echo_stdin"):
        raise ValueError("run_async() does not support echo_stdin")
    if options.get("in_stream") not in (None, False):
        raise ValueError("run_async() only supports disabled stdin")

    command = context._prefix_commands(command)  # pylint: disable=protected-access
    shell = options.get("shell") or "bash"
    encoding = options.get("encoding") or default_encoding()
    hide = normalize_hide(
        options.get("hide"), options.get("out_stream"), options.get("err_stream")
    )
    env_values = options.get("env") or {}
    env = (
        dict(env_values)
        if options.get("replace_env")
        else dict(os.environ, **env_values)
    )

    if options.get("echo"):
        print(options.get("echo_format", "{command}").format(command=command))
    if options.get("dry"):
        return Result(
            command=command,
            shell=shell,
            env=env,
            encoding=encoding,
            exited=0,
            hide=hide,
        )

    process = await asyncio.create_subprocess_shell(
        command,
        executable=shell,
        stdout=async_subprocess.PIPE,
        stderr=async_subprocess.PIPE,
        stdin=async_subprocess.DEVNULL,
        env=env,
    )
    try:
        communicate = process.communicate()
        if timeout is None:
            stdout, stderr = await communicate
        else:
            stdout, stderr = await asyncio.wait_for(communicate, timeout=timeout)
    except asyncio.TimeoutError as exc:
        await _terminate_process(process)
        result = _result(command, shell, env, encoding, process, b"", b"", hide)
        raise CommandTimedOut(result, timeout=timeout) from exc
    except asyncio.CancelledError:
        await _terminate_process(process)
        raise

    result = _result(command, shell, env, encoding, process, stdout, stderr, hide)
    _write_streams(result, options)
    if not result.ok and not options.get("warn"):
        raise UnexpectedExit(result)
    return result


async def _terminate_process(process: async_subprocess.Process) -> None:
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=1)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


def _result(
    command: str,
    shell: str,
    env: dict[str, str],
    encoding: str,
    process: async_subprocess.Process,
    stdout: bytes,
    stderr: bytes,
    hide: tuple[str, ...],
) -> Result:
    exited = process.returncode
    if exited is None:
        raise RuntimeError("Process completed without an exit code")
    return Result(
        stdout=stdout.decode(encoding, errors="replace"),
        stderr=stderr.decode(encoding, errors="replace"),
        command=command,
        shell=shell,
        env=env,
        encoding=encoding,
        exited=exited,
        hide=hide,
        pid=process.pid,
    )


def _write_streams(result: Result, options: dict[str, Any]) -> None:
    out_stream = options.get("out_stream") or sys.stdout
    err_stream = options.get("err_stream") or sys.stderr
    if "out" not in result.hide and out_stream is not False:
        out_stream.write(result.stdout)
        out_stream.flush()
    if "err" not in result.hide and err_stream is not False:
        err_stream.write(result.stderr)
        err_stream.flush()
