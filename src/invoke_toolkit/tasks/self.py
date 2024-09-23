import sys
from typing import List, Optional

from invoke import task
from invoke.context import Context

from invoke_toolkit.output import rich_exit

try:
    import hunter

    HUNTER_AVAILABLE = True
except ImportError:
    HUNTER_AVAILABLE = False


@task()
def trace(
    ctx: Context,
    query_: List[str] = [],
    verbose: bool = False,
    code: bool = True,
    vars: bool = True,
):
    """
    Enables tracing of execution of the tasks.
    Consider this as bash -x with selections.

    For more sophisticated calls use PYTHONHUNTER=xxx inv yyy
    Read more about it at: https://python-hunter.readthedocs.io/en/latest/introduction.html#activation
    """
    if not HUNTER_AVAILABLE:
        rich_exit("[bold]hunter[/bold] package not available")

    if not query_:
        query_ = ["module_sw=invoke_toolkit.tasks"]

    def build_query(a_string):
        key, value = a_string.split(
            "=",
        )
        kw = {key: value}
        return hunter.Query(**kw)

    queries = [build_query(query) for query in query_]
    if verbose:
        print(queries, file=sys.stderr)
    actions = []
    if code:
        actions.append(hunter.actions.CodePrinter())
    if vars:
        actions.append(hunter.actions.VarsSnooper())
    hunter.trace(*queries, actions=actions, stdlib=False)
