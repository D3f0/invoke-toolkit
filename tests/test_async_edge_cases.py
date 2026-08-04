"""Regression tests for async API edge cases."""

import asyncio

import pytest

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.testing import TestingToolkitProgram


def test_async_task_honors_cli_echo_config(capsys):
    @task()
    async def command(ctx: Context):
        result = await ctx.run("printf configured", hide=True)
        ctx.print(result.stdout)

    program = TestingToolkitProgram(namespace=ToolkitCollection(command))
    program.run(["", "-e", "command"], exit=False)
    output = capsys.readouterr()
    assert "configured" in output.out
    assert "printf configured" in output.err or "printf configured" in output.out


def test_async_run_rejects_interactive_stream():
    async def scenario():
        context = ToolkitContext()
        with pytest.raises(ValueError, match="disabled stdin"):
            await context.run_async("printf nope", in_stream=True)

    asyncio.run(scenario())


def test_async_run_cancellation_cleans_up():
    async def scenario():
        context = ToolkitContext()
        command = asyncio.create_task(context.run_async("sleep 10", hide=True))
        await asyncio.sleep(0.05)
        command.cancel()
        with pytest.raises(asyncio.CancelledError):
            await command

    asyncio.run(scenario())
