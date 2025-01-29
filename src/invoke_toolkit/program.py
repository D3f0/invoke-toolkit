"""
A CLI to create CLIs
"""

import inspect
import logging
import os
import sys

# if TYPE_CHECKING:
#     pass
from ast import Dict, literal_eval
from pathlib import Path
from types import ModuleType
from typing import (
    List,
    Optional,
)

from appdirs import user_data_dir
from invoke.context import Context
from invoke.exceptions import Exit, ParseError, UnexpectedExit
from invoke.parser import Argument
from invoke.program import Program
from invoke.util import debug
from rich import traceback as rich_traceback
from rich.logging import RichHandler

from invoke_toolkit.collections import InvokeCollection
from invoke_toolkit.executor import InvokeToolkitExecutor
from invoke_toolkit.output import console, rich_exit
from invoke_toolkit.utils.debug import enable_hunter_race


class InvokeToolkitProgram(Program):
    collection: InvokeCollection
    author: str = "InvokeToolkitTeam"

    def __init__(
        self,
        version=None,
        namespace=None,
        name=None,
        binary=None,
        loader_class=None,
        executor_class=InvokeToolkitExecutor,
        config_class=None,
        binary_names=None,
    ):
        super().__init__(
            version,
            namespace,
            name,
            binary,
            loader_class,
            executor_class,
            config_class,
            binary_names,
        )

    # We override the main invoke run functions but enabling
    # some opinionated features like rich tracebacks
    def run(self, argv: Optional[List[str]] = None, exit: bool = True) -> None:
        """
        Execute main CLI logic, based on ``argv``.

        :param argv:
            The arguments to execute against. May be ``None``, a list of
            strings, or a string. See `.normalize_argv` for details.

        :param bool exit:
            When ``False`` (default: ``True``), will ignore `.ParseError`,
            `.Exit` and `.Failure` exceptions, which otherwise trigger calls to
            `sys.exit`.

            .. note::
                This is mostly a concession to testing. If you're setting this
                to ``False`` in a production setting, you should probably be
                using `.Executor` and friends directly instead!

        .. versionadded:: 1.0
        """

        try:
            # Enable rich as early as possible
            self.enable_rich()

            # Create an initial config, which will hold defaults & values from
            # most config file locations (all but runtime.) Used to inform
            # loading & parsing behavior.

            self.create_config()
            # Parse the given ARGV with our CLI parsing machinery, resulting in
            # things like self.args (core args/flags), self.collection (the
            # loaded namespace, which may be affected by the core flags) and
            # self.tasks (the tasks requested for exec and their own
            # args/flags)
            self.parse_core(argv)
            # Enable tracing (like bash -x)
            self.enable_tracing()
            # Handle collection concerns including project config
            self.parse_collection()
            # Load plugins based on the core arguments
            self.load_plugins()
            # Parse remainder of argv as task-related input
            self.parse_tasks()
            # End of parsing (typically bailout stuff like --list, --help)
            self.parse_cleanup()
            # Update the earlier Config with new values from the parse step -
            # runtime config file contents and flag-derived overrides (e.g. for
            # run()'s echo, warn, etc options.)
            self.update_config()
            # Create an Executor, passing in the data resulting from the prior
            # steps, then tell it to execute the tasks.
            self.execute()
        except (UnexpectedExit, Exit, ParseError) as e:
            debug("Received a possibly-skippable exception: {!r}".format(e))
            # Print error messages from parser, runner, etc if necessary;
            # prevents messy traceback but still clues interactive user into
            # problems.
            if isinstance(e, ParseError):
                print(e, file=sys.stderr)
            if isinstance(e, Exit) and e.message:
                print(e.message, file=sys.stderr)
            if isinstance(e, UnexpectedExit) and e.result.hide:
                print(e, file=sys.stderr, end="")
            # Terminate execution unless we were told not to.
            if exit:
                if isinstance(e, UnexpectedExit):
                    code = e.result.exited
                elif isinstance(e, Exit):
                    code = e.code
                elif isinstance(e, ParseError):
                    code = 1
                sys.exit(code)
            else:
                debug("Invoked as run(..., exit=False), ignoring exception")
        except KeyboardInterrupt:
            sys.exit(1)  # Same behavior as Python itself outside of REPL

    def core_args(self) -> List[Argument]:
        """
        Adds the plugin flag to the core arguments
        """
        invoke_core_args: List[Argument] = super().core_args()
        toolkit_core_args = [
            Argument(
                names=("with", "W"),
                kind=list,
                default=[],
                help="Add a collection of tasks (plugin) to the collection. "
                "This can be a local folder or a git remote",
            ),
            Argument(
                names=("tracer", "x"), kind=bool, default=False, help="Enable tracer"
            ),
            # This argument cannot be parsed soon enough
            # Argument(
            #     names=("poor"),
            #     kind=bool,
            #     default=False,
            #     help="Disable rich integration",
            # ),
        ]

        return invoke_core_args + toolkit_core_args

    def enable_tracing(
        self,
    ) -> None:
        if self.args.tracer:
            enable_hunter_race()

    FORMAT = "%(message)s"

    def enable_rich(self):
        """Enable rich tracebacks"""
        poor = os.environ.get("INVOKE_POOR", "0")
        try:
            enable_rich = not literal_eval(poor)
        except Exception:
            enable_rich = True

        if enable_rich:
            rich_traceback.install()

            logging.basicConfig(
                level="INFO",
                format=self.FORMAT,
                datefmt="[%X]",
                handlers=[RichHandler()],
            )

    # Abandoning this idea for now
    # def create_config(self) -> None:
    #     """Adds the invoke-toolkit extra keys"""
    #     super().create_config()
    #     section = self.config.setdefault("invoke-toolkit", {})
    #     section["instance"] = self

    def load_plugins(self) -> None:
        if not self.collection:
            rich_exit("Can't find the main collection")
        from .collections import add_plugins

        for plugin in self.args["with"].value:
            console.log(f"Should load plugin {plugin}")
            add_plugins(
                None,
                plugin_dir=self.plugin_dir,
                plugin_ref=plugin,
                collection=self.collection,
            )

    def print_version(self) -> None:
        try:
            where_are_we = __file__
            parent = Path(where_are_we).parent
        except Exception:
            print("Error")
        ctx = Context()
        git = ctx.run(f"git -C {parent} status", warn=True, hide=True)
        if git.ok:
            version = self.version

        print("{} {}".format(self.name, version or "unknown"))

    @property
    def plugin_dir(self) -> Path:
        """Returns the base path where the plugins will be loaded"""
        appname = type(self).__name__
        location = user_data_dir(appname=appname, appauthor=self.author)
        path = Path(location) / "plugins"

        if not path.exists():
            path.mkdir(parents=True)
        return path


def get_caller_module() -> ModuleType:
    """
    From a script get the module it was called from
    """
    # Get the current frame
    current_frame = inspect.currentframe()
    # Get the caller's frame (1 level up in the stack)
    caller_frame = current_frame.f_back.f_back

    # Get the module name from the caller's frame
    module = inspect.getmodule(caller_frame)

    # Clean up the frame references to prevent memory leaks
    del current_frame
    del caller_frame

    return module


def script():
    from invoke import Task
    from invoke.collection import Collection

    caller_script = get_caller_module()
    tasks: Dict[str, Task] = {}
    for name, obj in inspect.getmembers(caller_script):
        if isinstance(obj, Task):
            tasks[name] = obj
    if not tasks:
        sys.exit(f"No task defined in {caller_script.__file__}")
    ns = Collection()
    for name, task in tasks.items():
        ns.add_task(task, name)
    program = Program(
        version="",
        namespace=ns,
    )
    program.run()
