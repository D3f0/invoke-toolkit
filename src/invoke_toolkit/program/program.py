"""
Main Program class extension
"""

__all__ = ["InvokeToolkitProgram"]

import sys
from importlib import metadata
from logging import getLogger
from typing import List, Optional

from rich.table import Table

from invoke_toolkit.log.logger import setup_rich_logging, setup_traceback_handler
from invoke_toolkit.output import get_console

setup_traceback_handler()
setup_rich_logging()
# To override the built-in logging settings from invoke
# we force rich to be installed first


from invoke.exceptions import Exit  # noqa: E402
from invoke.program import (  # noqa: E402
    Program,  # noqa: E402
    print_completion_script,  # noqa: E402
)
from invoke.util import debug  # noqa: E402

# Overrides that need to be imported afterwards
from invoke_toolkit.config import InvokeToolkitConfig  # noqa: E402
from invoke_toolkit.executor import InvokeToolkitExecutor  # noqa: E402


class InvokeToolkitProgram(Program):
    """Invoke Toolkit program providing rich output, package versioning and other features"""

    def __init__(
        self,
        version=None,
        namespace=None,
        name=None,
        binary=None,
        loader_class=None,
        executor_class=InvokeToolkitExecutor,
        config_class=InvokeToolkitConfig,
        binary_names=None,
    ):
        super().__init__(
            version or self.get_version(),
            namespace,
            name,
            binary,
            loader_class,
            executor_class,
            config_class,
            binary_names,
        )

    def get_version(self) -> str:
        """Compute version

        https://adamj.eu/tech/2025/07/30/python-check-package-version-importlib-metadata-version/
        """
        return metadata.version("invoke-toolkit")

    def parse_core(self, argv: Optional[List[str]]) -> None:
        debug("argv given to Program.run: {!r}".format(argv))  # pylint: disable=W1202
        self.normalize_argv(argv)

        # Obtain core args (sets self.core)
        self.parse_core_args()
        debug("Finished parsing core args")

        # Set interpreter bytecode-writing flag
        sys.dont_write_bytecode = not self.args["write-pyc"].value

        # Enable debugging from here on out, if debug flag was given.
        # (Prior to this point, debugging requires setting INVOKE_DEBUG).
        if self.args.debug.value:
            getLogger("invoke").setLevel("DEBUG")

        # Short-circuit if --version
        if self.args.version.value:
            debug("Saw --version, printing version & exiting")
            self.print_version()
            raise Exit

        # Print (dynamic, no tasks required) completion script if requested
        if self.args["print-completion-script"].value:
            print_completion_script(
                shell=self.args["print-completion-script"].value,
                names=self.binary_names,
            )
            raise Exit

    def print_columns(self, tuples, col_count: int | None = 2):
        col_count = col_count or max(len(t) for t in tuples)
        grid = Table.grid(expand=True)  # noqa: F821
        for _ in range(col_count):
            grid.add_column()
        for tup in tuples:
            grid.add_row(*tup)
        get_console().print(grid)
