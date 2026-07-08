"""Context object for invoke_toolkit tasks"""

import os
import subprocess
import sys
from contextlib import _GeneratorContextManager, contextmanager
from os import PathLike
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Iterator,
    Literal,
    NoReturn,
    Optional,
    Protocol,
    TypeVar,
    Union,
    overload,
)

import setproctitle
from invoke.context import Context
from invoke.util import debug
from rich import inspect

from invoke_toolkit.config import ToolkitConfig
from invoke_toolkit.config.status_helper import StatusHelper
from invoke_toolkit.output.console import get_console

from .types import BoundPrintProtocol, ContextRunProtocol

if TYPE_CHECKING:
    from rich.console import Console
    from rich.status import Status
    # from rich.console import RenderableType, StyleType

T = TypeVar("T")


class ConfigProtocol(Protocol):
    """Type annotated override"""

    status: Generator["Status", None, None]
    console: "Console"
    status_stop: Callable
    status_update: Callable
    print: BoundPrintProtocol

    def rich_exit(
        self, message: str = "Exited", exit_code: Optional[int] = 1
    ) -> NoReturn:
        """Rich exit"""

    def proctitle(self, title: str) -> Iterator[None]:
        """Context manager to set the process title"""


class ToolkitContext(Context, ConfigProtocol):
    """Type annotated override"""

    run: ContextRunProtocol
    _console: "Console"
    _config: ToolkitConfig
    _status_helper: StatusHelper

    # Override cd with proper type annotation to fix PathLike[Unknown] issue
    cd: Callable[
        [Union[PathLike[str], str]], _GeneratorContextManager[None, None, None]
    ]

    def __init__(
        self, config: Optional[ToolkitConfig] = None, remainder: str = ""
    ) -> None:
        super().__init__(config, remainder=remainder)
        self._set("_console", get_console())
        # Check if status is disabled in the config
        disabled = False
        show_command_output = False
        if config and hasattr(config, "get"):
            disabled = config.get("disable_status", False)
            show_command_output = config.get("show_command_output", False)
        self._set(
            "_status_helper",
            StatusHelper(
                console=self._console,
                disabled=disabled,
                show_command_output=show_command_output,
            ),
        )

    @property
    def console(self) -> "Console":
        """A console instance to do rich output"""
        console = get_console()
        return console

    # @contextmanager
    @property
    def status(self):
        """A rich Context manager to show progress on long running tasks"""
        return self._status_helper.status

    @property
    def status_update(
        self,
    ):
        """Updates the status."""
        return self._status_helper.status_update

    def status_stop(self) -> None:
        """
        Clears all status
        Helpful when debugging
        """
        return self._status_helper.status_stop()

    def rich_exit(
        self, message: str = "Exited", exit_code: Optional[int] = 1
    ) -> NoReturn:
        """An alternative to sys.exit that has rich output"""
        get_console().log(message)
        sys.exit(exit_code)

    @property
    def print(self):
        """Rich print, use square bracketed markup for color/highlights"""
        return get_console("out").print

    @property
    def print_err(self):
        """Rich print, use square bracketed markup for color/highlights"""
        return self._console.print

    def inspect(
        self,
        obj,
        *,
        # console: Optional["Console"] = None,
        title: Optional[str] = None,
        help_: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all_: bool = False,
        value: bool = True,
        stream: Literal["out"] | Literal["err"] = "err",
    ):
        """Runs inspect on an object"""
        assert stream in {"out", "err"}
        return inspect(
            obj,
            console=get_console(stream=stream),
            title=title,
            help=help_,
            methods=methods,
            docs=docs,
            private=private,
            dunder=dunder,
            sort=sort,
            all=all_,
            value=value,
        )

    @contextmanager
    def redact(
        self,
        streams: str | dict[str, list[str]],
        patterns: Optional[list[str]] = None,
    ) -> Iterator[None]:
        """
        This context manager will make the desired streams (out, err) replace
        environment values with their environment name.

        You must not change the local runner to keep this functionality.

        Redaction works only on environment variables that matches either as a
        `fnmatch` pattern or as a `regex` passed as `patterns`

        This can be used as for a specific stream
        ```python

        # For testing purposes
        os.environ.setdefault("SECRET_KEY", "dont_show")

        @task()
        def my_task(ctx: Context):
            with ctx.redact("out"):
                ctx.print(os.environ["SECRET_KEY"])
        ```

        For more grained control you can use the stream dictionary mode:

        ```python

        # For testing purposes
        os.environ.setdefault("SECRET_KEY", "dont_show")

        @task()
        def my_task(ctx: Context):
            with ctx.redact({"out": "*KEY"}):
                ctx.print(os.environ["SECRET_KEY"])
        ```

        Finally, if both streams need to be redactbed, to avoid repeating the keys,
        there's a convenience argument called patterns, which can provide a list of
        patterns. By default assumes `*`

        > If some redactbing was already defined, the previous patterns
        > will be replaced until the context manager is out of scope.

        """
        valid_streams = set(["out", "err"])
        stream_dict_backup = {}
        stream_dict_to_apply = {}
        if isinstance(streams, str):
            # Default to all environment variables if no patterns provided
            if not patterns:
                patterns = ["*"]

            for stream_name in streams.split(","):
                if stream_name not in valid_streams:
                    self.rich_exit(
                        f"redactbing can only work on out, err: given {streams}"
                    )
                stream_dict_to_apply[stream_name] = patterns

        elif isinstance(streams, dict):
            invalid = set(streams.keys()) - valid_streams
            if invalid:
                self.rich_exit(f"redactbing of invalid stream: {' '.join(invalid)}")
            stream_dict_to_apply = streams
        for stream_name, pattern_list in stream_dict_to_apply.items():
            console = get_console(
                stream_name  # type: ignore
            )
            if console.secret_patterns:
                stream_dict_backup[stream_name] = console.secret_patterns
                debug(f"Backing up {stream_name=} {console.secret_patterns=}")
            console.secret_patterns = pattern_list
        yield
        for stream_name, pattern_list in stream_dict_backup.items():
            console = get_console(
                stream_name  # type: ignore
            )
            debug(f"restoring {stream_name=} {pattern_list=}")
            console.secret_patterns = pattern_list

    def get_schema(self, schema_cls: type[T], path: str | None = None) -> T:
        """Get typed config schema, falling back to defaults if not configured.

        This is a convenience wrapper around `config.as_schema()` that handles
        the case when the config path doesn't exist by returning schema defaults.

        Args:
            schema_cls: The ConfigSchema class to use
            path: Config path (e.g., "app" or "app.database"). If None, uses
                  the schema's registered collection name.

        Returns:
            Instance of schema_cls populated from config or with defaults

        Example:
            @config_schema("myapp")
            class MyConfig(ConfigSchema):
                debug: bool = False

            @task
            def mytask(ctx: Context) -> None:
                config = ctx.get_schema(MyConfig)  # Uses "myapp" path
                # or
                config = ctx.get_schema(MyConfig, "custom.path")
        """

        # Determine path from schema if not provided
        if path is None:
            path = getattr(schema_cls, "__config_collection__", None)
            if path is None:
                raise ValueError(
                    f"No path provided and {schema_cls.__name__} has no "
                    "__config_collection__ attribute. Use @config_schema decorator "
                    "or provide path explicitly."
                )

        try:
            return self.config.as_schema(schema_cls, path)
        except KeyError:
            # Config path doesn't exist - return defaults
            return schema_cls()

    @contextmanager
    def proctitle(self, title: str) -> Iterator[None]:
        """
        Context manager to temporarily set the process title.

        When the context manager exits, the previous process title is restored.
        If running inside tmux ($TMUX is set), also updates the tmux window title.

        Example:
            @task()
            def my_task(ctx: Context):
                with ctx.proctitle("Processing files"):
                    # Long running operation
                    process_files()
                # Title is restored here

        Args:
            title: The process title to set
        """
        previous_title = setproctitle.getproctitle()
        in_tmux = os.environ.get("TMUX")
        previous_tmux_title = None

        if in_tmux:
            # Save current tmux window name
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#W"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                previous_tmux_title = result.stdout.strip()
            # Set new tmux window name
            subprocess.run(
                ["tmux", "rename-window", title],
                check=False,
            )

        try:
            setproctitle.setproctitle(title)
            yield
        finally:
            setproctitle.setproctitle(previous_title)
            if in_tmux and previous_tmux_title is not None:
                subprocess.run(
                    ["tmux", "rename-window", previous_tmux_title],
                    check=False,
                )

    # Type overloads for get_config_value - returns T when no exit params
    @overload
    def get_config_value(
        self,
        path: str,
        default: T = ...,  # type: ignore[assignment]
        exit_message: None = None,
        exit_code: None = None,
        required: bool = False,
    ) -> Any | T: ...

    # Type hints NoReturn when exit_message provided
    @overload
    def get_config_value(
        self,
        path: str,
        default: Any = ...,
        exit_message: str = ...,
        exit_code: Optional[int] = None,
        required: bool = False,
    ) -> Any | NoReturn: ...

    # Type hints NoReturn when exit_code provided
    @overload
    def get_config_value(
        self,
        path: str,
        default: Any = ...,
        exit_message: None = None,
        exit_code: int = ...,
        required: bool = False,
    ) -> Any | NoReturn: ...

    # Type hints NoReturn when required=True
    @overload
    def get_config_value(
        self,
        path: str,
        default: Any = ...,
        exit_message: Optional[str] = None,
        exit_code: Optional[int] = None,
        required: bool = True,
    ) -> Any | NoReturn: ...

    def get_config_value(
        self,
        path: str,
        default: Any = ...,
        exit_message: Optional[str] = None,
        exit_code: Optional[int] = None,
        required: bool = False,
    ) -> Any:
        """Get a configuration value from config with dot notation support.

        This is a convenience method that wraps invoke_toolkit.config.get_config_value.
        See that function for full documentation.

        Args:
            path: Dot-separated path to the config value (e.g., 'database.host')
            default: Default value if path not found
            exit_message: Custom message when value required but missing
            exit_code: Exit code for ctx.rich_exit() when missing
            required: Whether value is required (exits if missing)

        Returns:
            The config value if found, otherwise default value.

        Example:
            @task()
            def my_task(ctx: Context) -> None:
                db_host = ctx.get_config_value("database.host", default="localhost")
                api_key = ctx.get_config_value("api.key", required=True)
        """
        # Import here to avoid circular imports
        from invoke_toolkit.config.config import (  # pylint: disable=import-outside-toplevel
            _UNDEFINED_DEFAULT,
            get_config_value as _get_config_value,
        )

        # Handle the default sentinel - ellipsis means "use undefined default"
        if default is ...:
            default = _UNDEFINED_DEFAULT
        return _get_config_value(self, path, default, exit_message, exit_code, required)
