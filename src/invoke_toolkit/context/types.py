"""
Type annotations for finding out what's there in ctx.attribute
"""

import sys
from typing import IO, Any, Optional, Union

from invoke.runners import Result
from invoke.watchers import StreamWatcher
from rich.console import JustifyMethod, OverflowMethod, Style
from typing_extensions import Annotated, Protocol


class BoundPrintProtocol(Protocol):
    def __call__(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: Optional[Union[str, Style]] = None,  # noqa: F821
        justify: Optional[JustifyMethod] = None,
        overflow: Optional[OverflowMethod] = None,
        no_wrap: Optional[bool] = None,
        emoji: Optional[bool] = None,
        markup: Optional[bool] = None,
        highlight: Optional[bool] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        crop: bool = True,
        soft_wrap: Optional[bool] = None,
        new_line_start: bool = False,
    ) -> None: ...


class ContextRunProtocol(Protocol):
    """This is a protocol describing the invoke.runners.Local.run arguments.
    The description have been shortened.
    """

    def __call__(
        self,
        command: str,
        *,
        asynchronous: bool = False,
        disown: bool = False,
        dry: bool = False,
        echo: Annotated[
            bool,
            """
            Controls whether `.run` prints the command string to local stdout
            prior to executing it. Default: ``False``.
            """,
        ] = False,
        echo_format: Annotated[
            str,
            """
            A string, which when passed to Python's inbuilt ``.format`` method,
            will change the format of the output when ``run.echo`` is set to
            true.

            Currently, only ``{command}`` is supported as a parameter.

            Defaults to printing the full command string in ANSI-escaped bold.
            """,
        ] = "",
        echo_stdin: Annotated[
            bool,
            """
            Whether to write data from ``in_stream`` back to ``out_stream``.

            In other words, in normal interactive usage, this parameter
            controls whether Invoke mirrors what you type back to your
            terminal.""",
        ] = False,
        encoding: Annotated[
            str,
            """
            Override auto-detection of which encoding the subprocess is using
            for its stdout/stderr streams (which defaults to the return value
            of `default_encoding`).
            """,
        ] = "",
        err_stream: Annotated[
            Any,
            """
            Same as ``out_stream``, except for standard error, and defaulting
            to ``sys.stderr``.
            """,
        ] = "",
        env: Annotated[
            Optional[dict[str, str]],
            """
            By default, subprocesses receive a copy of Invoke's own environment
            (i.e. ``os.environ``). Supply a dict here to update that child
            environment.

            For example, ``run('command', env={'PYTHONPATH':
            '/some/virtual/env/maybe'})`` would modify the ``PYTHONPATH`` env
            var, with the rest of the child's env looking identical to the
            parent.
            """,
        ] = None,
        fallback: Annotated[
            bool,
            """
            Controls auto-fallback behavior re: problems offering a pty when
            ``pty=True``. Whether this has any effect depends on the specific
            `Runner` subclass being invoked. Default: ``True``.
            """,
        ] = False,
        hide: Annotated[
            bool,
            """
            Allows the caller to disable ``run``'s default behavior of copying
            the subprocess' stdout and stderr to the controlling terminal.
            Specify ``hide='out'`` (or ``'stdout'``) to hide only the stdout
            stream, ``hide='err'`` (or ``'stderr'``) to hide only stderr, or
            ``hide='both'`` (or ``True``) to hide both streams.
            """,
        ] = False,
        in_stream: Annotated[
            Union[None, IO, bool],
            """
            A file-like stream object to used as the subprocess' standard
            input. If ``None`` (the default), ``sys.stdin`` will be used.

            If ``False``, will disable stdin mirroring entirely (though other
            functionality which writes to the subprocess' stdin, such as
            autoresponding, will still function.) Disabling stdin mirroring can
            help when ``sys.stdin`` is a misbehaving non-stream object, such as
            under test harnesses or headless command runners.
            """,
        ] = sys.stdin,
        out_stream: Annotated[
            Union[None, IO],
            """
            A file-like stream object to which the subprocess' standard output
            should be written. If ``None`` (the default), ``sys.stdout`` will
            be used.
            """,
        ] = sys.stdout,
        pty: Annotated[
            bool,
            """
            By default, ``run`` connects directly to the invoked process and
            reads its stdout/stderr streams. Some programs will buffer (or even
            behave) differently in this situation compared to using an actual
            terminal or pseudoterminal (pty). To use a pty instead of the
            default behavior, specify ``pty=True``.
            """,
        ] = False,
        replace_env: Annotated[
            bool,
            """
            When ``True``, causes the subprocess to receive the dictionary
            given to ``env`` as its entire shell environment, instead of
            updating a copy of ``os.environ`` (which is the default behavior).
            Default: ``False``.
            """,
        ] = False,
        shell: Annotated[
            str,
            """
            Which shell binary to use. Default: ``/bin/bash`` (on Unix;
            ``COMSPEC`` or ``cmd.exe`` on Windows.)
            """,
        ] = "",
        timeout: Annotated[
            Optional[Union[int, float]],
            """
            Cause the runner to submit an interrupt to the subprocess and raise
            `.CommandTimedOut`, if the command takes longer than ``timeout``
            seconds to execute. Defaults to ``None``, meaning no timeout.
            """,
        ] = None,
        warn: Annotated[
            bool,
            """
            Whether to warn and continue, instead of raising
            `.UnexpectedExit`, when the executed command exits with a
            nonzero status. Default: ``False``.
            """,
        ] = False,
        watchers: Annotated[
            list[StreamWatcher],
            """
            A list of `.StreamWatcher` instances which will be used to scan the
            program's ``stdout`` or ``stderr`` and may write into its ``stdin``
            (typically ``bytes`` objects) in response to patterns or other
            heuristics.
            """,
        ] = [],
    ) -> Result:
        """
        Execute ``command``, returning an instance of `Result` once complete.

        By default, this method is synchronous (it only returns once the
        subprocess has completed), and allows interactive keyboard
        communication with the subprocess.

        It can instead behave asynchronously (returning early & requiring
        interaction with the resulting object to manage subprocess lifecycle)
        if you specify ``asynchronous=True``. Furthermore, you can completely
        disassociate the subprocess from Invoke's control (allowing it to
        persist on its own after Python exits) by saying ``disown=True``. See
        the per-kwarg docs below for details on both of these.
        """
