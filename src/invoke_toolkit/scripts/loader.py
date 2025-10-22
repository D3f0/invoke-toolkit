"""
Run scripts with https://peps.python.org/pep-0723/
"""

import inspect
from types import FrameType
from typing import List, Optional

from invoke.tasks import Task

from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.output.utils import rich_exit
from invoke_toolkit.program import ToolkitProgram


def script(argv: Optional[List[str]] = None, exit: bool = True) -> None:
    r"""Allows to call .py files directly without invoke-toolkit/it command.

    You can:

    * Run the task file with uv run/pipx run
    * Run with **shebang**, `#!/usr/bin/env -S uv run --script` as described in
      [this post](https://www.serhii.net/dtb/250128-2149-using-uv-as-shebang-line/)

    ```python
    #!/usr/bin/env -S uv run --script
    # mytasks.py

    from invoke_toolkit import script
    from invoke_toolkit import task, Context

    @task()
    def checkmate(ctx: Context):
        ctx.run("hello")

    if __name__ == "__main__":
        # if you don't plan tu use uv run, you can avoid the if __name__
        script()
    ```

    Then run the script with `uv run --with invoke-toolkit mytasks.py

    """
    current_frame = inspect.currentframe()
    assert current_frame is not None
    if current_frame.f_back is not None:
        frame: FrameType = current_frame.f_back
    else:
        rich_exit("Inspection failed trying to get previous frame")
    f_locals = frame.f_locals
    if f_locals is None:
        rich_exit(f"Can't inspect the {__file__} for tasks")
    c = ToolkitCollection()
    for _, obj in f_locals.items():
        if isinstance(obj, Task):
            c.add_task(obj)
    p = ToolkitProgram(namespace=c)
    return p.run(argv=argv, exit=exit)
