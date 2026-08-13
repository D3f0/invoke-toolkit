from __future__ import annotations

from invoke_toolkit import Context, Field, task

received: list[int] = []


@task
def future_count(ctx: Context, count: int = Field(default=3)) -> None:
    del ctx
    received.append(count)
