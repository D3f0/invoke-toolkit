"""Context object for invoke_toolkit tasks"""

from contextlib import contextmanager
import sys
from invoke.context import Context
from typing import (
    Callable,
    Generator,
    Iterator,
    Literal,
    NoReturn,
    Optional,
    Protocol,
    TYPE_CHECKING,
    Union,
)
from invoke.util import debug
from invoke_toolkit.config import ToolkitConfig
from invoke_toolkit.config.status_helper import StatusHelper
from invoke_toolkit.output.console import get_console
from .types import BoundPrintProtocol, ContextRunProtocol


from rich import inspect

if TYPE_CHECKING:
    from rich.console import Console
    from rich.status import Status
    # from rich.console import RenderableType, StyleType


class ConfigProtocol(Protocol):
    """Type annotated override"""

    status: Generator["Status", None, None]
    console: "Console"
    status_stop: Callable
    status_update: Callable
    # rich_exit: Callable[[str, Optional[int]], NoReturn]
    rich_exit: Callable[[str, int], NoReturn]
    print: BoundPrintProtocol


class ToolkitContext(Context, ConfigProtocol):
    """Type annotated override"""

    run: ContextRunProtocol
    _console: "Console"
    _config: ToolkitConfig
    _status_helper: StatusHelper

    def __init__(self, config: Optional[ToolkitConfig] = None) -> None:
        super().__init__(config)
        self._set("_console", get_console())
        self._set("_status_helper", StatusHelper(console=self._console))

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

    def rich_exit(self, message: str = "Exited", exit_code=1) -> NoReturn:
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
        stream: Union[Literal["out"], Literal["err"]] = "err",
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
    def scrub(
        self,
        streams: Union[str, dict[str, list[str]]],
        patterns: Optional[list[str]] = None,
    ) -> Iterator[None]:
        """
        This context manager will make the desired streams (out, err) to remove any
        *"sensitive values"*.

        Sensitive information is any environment variable that matches either as a
        `fnmatch` pattern or as a `regex`.

        This can be used as for a specific stream
        ```python

        # For testing purposes
        os.environ.setdefault("SECRET_KEY", "dont_show")

        @task()
        def my_task(ctx: Context):
            with ctx.scrub("out"):
                ctx.print(os.environ["SECRET_KEY"])
        ```

        For more grained control you can use the stream dictionary mode:

        ```python

        # For testing purposes
        os.environ.setdefault("SECRET_KEY", "dont_show")

        @task()
        def my_task(ctx: Context):
            with ctx.scrub({"out": "*KEY"}):
                ctx.print(os.environ["SECRET_KEY"])
        ```

        Finally, if both streams need to be scrubbed, to avoid repeating the keys,
        there's a convenience argument called patterns, which can provide a list of
        patterns. By default assumes `*`

        > If some scrubbing was already defined, the previous patterns
        > will be replaced until the context manager is out of scope.

        """
        valid_streams = set(["out", "err"])
        stream_dict_backup = {}
        stream_dict_to_apply = {}
        if isinstance(streams, str):
            if not patterns:
                self.rich_exit("patterns are empty")

            for stream_name in streams.split(","):
                if stream_name not in valid_streams:
                    self.rich_exit(
                        f"scrubbing can only work on out, err: given {streams}"
                    )
                stream_dict_to_apply[stream_name] = patterns

        elif isinstance(streams, dict):
            invalid = set(streams.keys()) - valid_streams
            if invalid:
                self.rich_exit(f"scrubbing of invalid stream: {' '.join(invalid)}")
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
