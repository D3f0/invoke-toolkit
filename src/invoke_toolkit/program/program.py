"""
The Program class runs the CLI. It can load a single tasks.py file
using a filesystem loader or a base collection.
It allows three classes to be parametrized: Loader, Config and Executor
"""

__all__ = ["InvokeToolkitProgram"]

import inspect
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


from invoke.exceptions import CollectionNotFound, Exit
from invoke.parser import Argument
from invoke.program import (
    Program,
    print_completion_script,
)
from invoke.util import debug

from invoke_toolkit.collections import InvokeToolkitCollection

# Overrides that need to be imported afterwards
from invoke_toolkit.config import InvokeToolkitConfig
from invoke_toolkit.executor import InvokeToolkitExecutor


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

        [see more](https://adamj.eu/tech/2025/07/30/python-check-package-version-importlib-metadata-version/)
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
        print = get_console("out").print
        col_count = col_count or max(len(t) for t in tuples)
        grid = Table.grid(expand=True, padding=(0, 4))  # noqa: F821
        for _ in range(col_count):
            grid.add_column()
        for tup in tuples:
            grid.add_row(*tup)
        print(grid)

    def print_task_help(self, name: str) -> None:
        """
        Print help for a specific task, e.g. ``inv --help <taskname>``.

        .. versionadded:: 1.0
        """
        # Setup
        print = get_console("out").print  # pylint: disable=redefined-builtin
        ctx = self.parser.contexts[name]
        tuples = ctx.help_tuples()
        docstring = inspect.getdoc(self.collection[name])
        header = "Usage: {} [--core-opts] {} {}[other tasks here ...]"
        opts = "[--options] " if tuples else ""
        print(header.format(self.binary, name, opts))
        print("")
        print("[yellow]Docstring:[/yellow]")
        if docstring:
            # Really wish textwrap worked better for this.
            for line in docstring.splitlines():
                if line.strip():
                    print(self.leading_indent + line)
                else:
                    print("")
            print("")
        else:
            print(self.leading_indent + "none")
            print("")
        print("Options:")
        if tuples:
            self.print_columns(tuples)
        else:
            print(self.leading_indent + "none")
            print("")

    def core_args(self) -> List["Argument"]:
        """
        Return default core `.Argument` objects, as a list.

        .. versionadded:: 1.0
        """
        # Arguments present always, even when wrapped as a different binary
        args = super().core_args()
        args.append(
            Argument(
                names=("internal-col", "x"),
                kind=bool,
                default=False,
                help="Loads the internal invoke-toolkit collections",
            )
        )
        return args

    def load_collection(self) -> None:
        """
        Load a task collection based on parsed core args, or die trying.

        Ensures that the type is InvokeToolkitCollection for correctness.
        """
        # NOTE: start, coll_name both fall back to configuration values within
        # Loader (which may, however, get them from our config.)
        start = self.args["search-root"].value
        loader = self.loader_class(  # type: ignore
            config=self.config, start=start
        )
        coll_name = self.args.collection.value
        try:
            module, parent = loader.load(coll_name)
            # This is the earliest we can load project config, so we should -
            # allows project config to affect the task parsing step!
            # TODO: is it worth merging these set- and load- methods? May
            # require more tweaking of how things behave in/after __init__.
            self.config.set_project_location(parent)
            self.config.load_project()
            self.collection = InvokeToolkitCollection.from_module(
                module,
                loaded_from=parent,
                auto_dash_names=self.config.tasks.auto_dash_names,
            )
        except CollectionNotFound as e:
            raise Exit("Can't find any collection named {!r}!".format(e.name))

        if self.args["internal-col"].value:
            debug("Trying to load internal invoke-toolkit collections")
            InvokeToolkitCollection.from_package(  # pylint: disable=unexpected-keyword-arg
                "invoke_toolkit.extensions.tasks",
                self.collection,
            )
