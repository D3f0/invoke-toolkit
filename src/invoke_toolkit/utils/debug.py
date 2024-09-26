import hunter
from typing import List
import logging

logger = logging.getLogger(__name__)


def enable_hunter_race(
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
    logger.debug("Enabling tracing")
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
