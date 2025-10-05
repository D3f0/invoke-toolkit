from typing import Optional, List
from invoke.program import Program
from invoke.collection import Collection
from invoke.tasks import Task
import inspect


def run(argv: Optional[List[str]] = None, exit: bool = True) -> None:
    """When called the file actas as it were called with invoke"""
    locals = inspect.currentframe().f_back.f_locals
    c = Collection()
    for name, obj in locals.items():
        if isinstance(obj, Task):
            c.add_task(obj)
    p = Program(namespace=c)
    return p.run(argv=argv, exit=exit)
