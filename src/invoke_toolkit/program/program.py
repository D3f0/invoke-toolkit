"""
The Program class runs the CLI. It can load a single tasks.py file
using a filesystem loader or a base collection.
It allows three classes to be parametrized: Loader, Config and Executor
"""

__all__ = ["ToolkitProgram"]

import inspect
import re
import sys
from importlib import metadata
from logging import getLogger
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from rich.table import Table

from invoke_toolkit.log.logger import setup_rich_logging, setup_traceback_handler
from invoke_toolkit.output import get_console

setup_traceback_handler()
setup_rich_logging()
# To override the built-in logging settings from invoke
# we force rich to be installed first


from invoke.completion.complete import complete
from invoke.exceptions import CollectionNotFound, Exit, ParseError, UnexpectedExit
from invoke.parser import Argument
from invoke.program import (
    Program,
    print_completion_script,
)
from invoke.util import debug

from invoke_toolkit.collections import ToolkitCollection

# Overrides that need to be imported afterwards
from invoke_toolkit.config import ToolkitConfig
from invoke_toolkit.executor import ToolkitExecutor

EMPTY_COLLECTION_NAME = "_empty"


class ToolkitProgram(Program):
    """Invoke Toolkit program providing rich output, package versioning and other features"""

    def __init__(
        self,
        version=None,
        namespace=None,
        name=None,
        binary=None,
        loader_class=None,
        executor_class=ToolkitExecutor,
        config_class=ToolkitConfig,
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
            # Handle collection concerns including project config
            self.parse_collection()
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
            print_err = get_console("err").print
            if isinstance(e, ParseError):
                print_err(e)
            if isinstance(e, Exit) and e.message:
                print_err(e.message)
            if isinstance(e, UnexpectedExit) and e.result.hide:
                print_err(e, end="")
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

    def setup_consoles(self):
        """Pre-populate the console objects"""
        patterns = self.args["redact_pattern"].value
        out, err = self.args.redact_stdout.value, self.args.redact_stderr.value
        enable_all = False
        if not patterns:
            if out or err:
                get_console("err").print(
                    "--redact-patter was not passed, no secret redactbing"
                )
            return
        if not out and not err:
            enable_all = True

        if out or enable_all:
            debug(f"Setting secret redactbing in stdout with {patterns=}")
            get_console("out").secret_patterns = patterns
        if err or enable_all:
            debug(f"Setting secret redactbing in stderr with {patterns=}")
            get_console("err").secret_patterns = patterns

    def parse_core(self, argv: Optional[List[str]]) -> None:
        debug("argv given to Program.run: {!r}".format(argv))  # pylint: disable=W1202
        self.normalize_argv(argv)

        # Obtain core args (sets self.core)
        self.parse_core_args()
        # Ensure the cache of consoles is pre-configured
        debug("Finished parsing core args")
        self.setup_consoles()

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

    def parse_collection(self):
        """
        Load a tasks collection & project-level config.

        .. versionadded:: 1.0
        """
        super().parse_collection()

        if self.args["internal-col"].value:
            debug("Trying to load internal invoke-toolkit collections")
            ToolkitCollection.from_package(  # pylint: disable=unexpected-keyword-arg
                "invoke_toolkit.extensions.tasks",
                self.collection,  # type: ignore
            )

    def print_columns(self, tuples, col_count: int | None = 2):
        print = get_console("out").print

        def escape_bool_flags(match: re.Match) -> str:
            prefix, suffix = match.groups()
            return f"{prefix}\\{suffix}"

        col_count = col_count or max(len(t) for t in tuples)
        grid = Table.grid(expand=True, padding=(0, 4))  # noqa: F821
        for _ in range(col_count):
            grid.add_column()
        for tup in tuples:
            # Escape Rich markup characters (e.g., square brackets) in tuple values
            first_part, *tail = tup

            first_part = re.sub(r"(--)(\[[\w\s#\/-]+])", escape_bool_flags, first_part)
            escaped_tup = [
                first_part,
            ] + tail
            # escaped_tup = tuple(escape(str(t)) for t in tup)
            grid.add_row(*escaped_tup)
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
        toolkit_program_arguments = [
            Argument(
                names=("internal-col", "x"),
                kind=bool,
                default=False,
                help="Loads the internal invoke-toolkit collections",
            ),
            Argument(
                names=("redact_stdout", "So"),
                kind=bool,
                default=False,
                help="Prevents console to print secrets to [green]stdout[/green]",
            ),
            Argument(
                names=("redact_stderr", "Se"),
                kind=bool,
                default=False,
                help="Prevents console to print secrets to [yellow]stderr[/yellow]",
            ),
            Argument(
                names=("redact_pattern", "Sp"),
                kind=list,
                default=[],
                help="Defines which patterns should be redactbed, such as *_API*KEY or regexes. Settings this alone enables "
                "redactbing both for [green]stdout[/green] and [yellow]stderr[/yellow]",
            ),
        ]
        args.extend(toolkit_program_arguments)
        return args

    def load_collection(self) -> None:
        """
        Load a task collection based on parsed core args, or die trying.

        Ensures that the type is ToolkitCollection for correctness.
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
            self.collection = ToolkitCollection.from_module(
                module,
                loaded_from=parent,
                auto_dash_names=self.config.tasks.auto_dash_names,
            )
        except CollectionNotFound as e:
            if not self.args["internal-col"].value:
                raise Exit(
                    (
                        "Can't find any collection named [red]{name!r}[/red].\n"
                        "You can create a script with [yellow]{cmd} -x create.script --help[/yellow]\n"
                        "You can create a script with [yellow]{cmd} -x create.package --help[/yellow]\n"
                    ).format(name=e.name, cmd=self.command_name)
                )
            debug("No collection found, will checking for internal")
            self.collection = ToolkitCollection(EMPTY_COLLECTION_NAME)

        # if self.collection.name == EMPTY_COLLECTION_NAME:
        #     debug("Setting the list flag, as the desired collection name was not found")
        #     self.core_args()
        #     self.args["list"].set_value(True, cast=False)

    @property
    def command_name(self) -> str:
        """Command that was used to run the program"""
        assert self.argv
        command, *_ = self.argv
        cmd = Path(command).stem
        return cmd

    @property
    def flat_args(self) -> Dict[str, Union[bool, int, str, List[str]]]:
        """Flat arguments"""
        return {name: arg.value for name, arg in self.args.items()}

    def parse_cleanup(self) -> None:
        """
        Post-parsing, pre-execution steps such as --help, --list, etc.
        Accept -x without any available tasks
        """

        halp = self.args.help.value

        # Core (no value given) --help output (only when bundled namespace)
        if halp is True:
            debug("Saw bare --help, printing help & exiting")
            self.print_help()
            raise Exit

        # Print per-task help, if necessary
        if halp:
            if halp in self.parser.contexts:
                msg = "Saw --help <taskname>, printing per-task help & exiting"
                debug(msg)
                self.print_task_help(halp)
                raise Exit
            else:
                # TODO: feels real dumb to factor this out of Parser, but...we
                # should?
                raise ParseError("No idea what '{}' is!".format(halp))

        # Print discovered tasks if necessary
        list_root = self.args.list.value  # will be True or string

        self.list_format = self.args["list-format"].value
        self.list_depth = self.args["list-depth"].value
        if list_root:
            # Not just --list, but --list some-root - do moar work
            if isinstance(list_root, str):
                self.list_root = list_root
                try:
                    sub = self.collection.subcollection_from_path(list_root)
                    self.scoped_collection = sub
                except KeyError:
                    msg = "Sub-collection '{}' not found!"
                    raise Exit(msg.format(list_root))
            self.list_tasks()
            raise Exit

        # Print completion helpers if necessary
        if self.args.complete.value:
            complete(
                names=self.binary_names,
                core=self.core,
                initial_context=self.initial_context,
                collection=self.collection,
                # NOTE: can't reuse self.parser as it has likely been mutated
                # between when it was set and now.
                parser=self._make_parser(),
            )

        # Fallback behavior if no tasks were given & no default specified
        # (mostly a subroutine for overriding purposes)
        # NOTE: when there is a default task, Executor will select it when no
        # tasks were found in CLI parsing.
        if not self.tasks and not self.collection.default:
            self.no_tasks_given()

    def display_with_columns(
        self, pairs: Sequence[Tuple[str, Optional[str]]], extra: str = ""
    ) -> None:
        print = get_console("out").print
        root = self.list_root
        print("{}:\n".format(self.task_list_opener(extra=extra)))
        self.print_columns(pairs)
        # TODO: worth stripping this out for nested? since it's signified with
        # asterisk there? ugggh
        default = self.scoped_collection.default
        if default:
            specific = ""
            if root:
                specific = " '{}'".format(root)
                default = ".{}".format(default)
            # TODO: trim/prefix dots
            print("Default{} task: [bold]{}[bold]\n".format(specific, default))
