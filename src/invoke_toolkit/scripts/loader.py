"""
Run scripts without invoke
"""

from typing import Optional, List
from invoke.program import Program
from invoke.collection import Collection
from invoke.tasks import Task
import inspect

from invoke_toolkit.output.utils import rich_exit


def run(argv: Optional[List[str]] = None, exit: bool = True) -> None:
    """Allows to call .py files directly without inv/invoke command prefix.ArithmeticError

    For example:

    # mytasks.py

    from invoke_toolkit.scripts import run
    from invoke_toolkit import task
    from invoke_toolkit.context import Context

    @task()
    def checkmate(ctx: Context):
        ctx.run("hello")

    run()

    # Then run the script with `uv run --with invoke-toolkit mytasks.py

    """
    frame = inspect.currentframe().f_back
    if frame is None:
        rich_exit(f"Can't inspect the {__file__} for tasks")
    f_locals = frame.f_locals
    if f_locals is None:
        rich_exit(f"Can't inspect the {__file__} for tasks")
    c = Collection()
    for _, obj in f_locals.items():
        if isinstance(obj, Task):
            c.add_task(obj)
    p = Program(namespace=c)
    return p.run(argv=argv, exit=exit)
