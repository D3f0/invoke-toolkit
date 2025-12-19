"""
Run scripts with https://peps.python.org/pep-0723/
"""

import inspect
import traceback
from types import FrameType
from typing import List, Optional

from invoke.tasks import Task
from invoke.util import debug

from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.output.utils import rich_exit
from invoke_toolkit.program import ToolkitProgram


def script(
    argv: Optional[List[str]] = None,
    exit: bool = True,
    config_prefix: Optional[str] = None,
) -> None:
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

    Args:
        argv: The arguments to execute. Optional list of strings.
        exit: Whether to call sys.exit() after execution. Defaults to True.
        config_prefix: Optional config prefix for finding config files. If provided,
            ToolkitConfig will look for config files with this prefix
            (e.g., prefix="myapp" looks for "myapp.yml", "myapp.yaml", etc.)
            Default is "invoke" if not specified.
    """
    # Prevent double calls for simple task that call invoke_toolkit.script()
    # at the module level without `if __name__ == "__main__"`
    #
    # from invoke_toolkit import task, Context, script
    #
    # @task()
    # def foo(ctx: Context):
    #     ctx.run("echo hello")
    #
    # script()

    for i, frame_summary in enumerate(traceback.extract_stack()):
        # rich.print(i)
        # rich.inspect(frame_summary)
        # breakpoint()
        if frame_summary.name == "parse_collection":
            debug(
                "Skipping script() call to prevent double execution, in "
                + f"frame {i}, {frame_summary}"
            )
            return None
    current_frame = inspect.currentframe()
    assert current_frame is not None
    if current_frame.f_back is not None:
        frame: FrameType = current_frame.f_back
    else:
        rich_exit("Inspection failed trying to get previous frame")
    f_locals = frame.f_locals
    if not f_locals:
        rich_exit(f"Can't inspect the {__file__} for tasks")
    c = ToolkitCollection()
    for _, obj in f_locals.items():
        if isinstance(obj, Task):
            c.add_task(obj)

    # Create custom config class with the specified prefix if provided
    if config_prefix:
        from invoke_toolkit.config import (  # pylint: disable=import-outside-toplevel
            ToolkitConfig,
        )

        class CustomConfig(ToolkitConfig):  # type: ignore[misc]
            prefix = config_prefix

        p = ToolkitProgram(namespace=c, config_class=CustomConfig)
    else:
        p = ToolkitProgram(namespace=c)
    return p.run(argv=argv, exit=exit)
