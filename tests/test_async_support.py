"""Tests for native async task and command support."""

import asyncio

import pytest

from invoke_toolkit import Context, task
from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.context.async_tools import AsyncGatherScope
from invoke_toolkit.testing import TestingToolkitProgram
from invoke_toolkit.collections import ToolkitCollection


def test_run_async_returns_invoke_result():
    async def scenario():
        context = ToolkitContext()
        result = await context.run_async("printf hello", hide=True)
        assert result.ok
        assert result.stdout == "hello"
        assert result.exited == 0

    asyncio.run(scenario())


def test_run_async_warn_returns_failed_result():
    async def scenario():
        context = ToolkitContext()
        result = await context.run_async("exit 3", hide=True, warn=True)
        assert result.failed
        assert result.exited == 3

    asyncio.run(scenario())


def test_gather_scope_preserves_submission_order():
    async def scenario():
        context = ToolkitContext()
        async with context.gather() as gather:
            first = gather(context.run_async("sleep .02; printf first", hide=True))
            second = gather(context.run_async("printf second", hide=True))
        assert await first
        assert await second
        assert gather.results[0].stdout == "first"
        assert gather.results[1].stdout == "second"

    asyncio.run(scenario())


def test_gather_scope_cancels_remaining_work():
    async def scenario():
        scope = AsyncGatherScope()

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("boom")

        async def wait():
            await asyncio.sleep(10)

        with pytest.raises(RuntimeError, match="boom"):
            async with scope as gather:
                gather(fail())
                gather(wait())

    asyncio.run(scenario())


def test_async_task_runs_from_program(capsys):
    @task()
    async def async_task(ctx: Context):
        result = await ctx.run("printf task", hide=True)
        ctx.print(result.stdout)
        return result.exited

    program = TestingToolkitProgram(namespace=ToolkitCollection(async_task))
    program.run(["", "async-task"], exit=False)
    assert "task" in capsys.readouterr().out


def test_sync_task_run_remains_synchronous():
    @task()
    def sync_task(ctx: Context):
        result = ctx.run("printf sync", hide=True)
        return result.stdout

    program = TestingToolkitProgram(namespace=ToolkitCollection(sync_task))
    program.run(["", "sync-task"], exit=False)
    assert sync_task.called
