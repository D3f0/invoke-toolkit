"""
Config object used for invoke attribute resolution
in tasks.
"""

import array
import errno
import sys
from threading import Lock
from typing import IO, TYPE_CHECKING

from invoke.runners import Local, ready_for_reading
from invoke.terminals import stdin_is_foregrounded_tty
from invoke.util import debug, has_fileno, isatty
from rich.syntax import Syntax

from invoke_toolkit.output import get_console

if sys.platform != "win32":
    import fcntl
    import termios
else:
    fcntl = None  # pylint: disable=invalid-name
    termios = None  # pylint: disable=invalid-name

if TYPE_CHECKING:
    from invoke_toolkit.config.status_helper import StatusHelper


_PTY_STDIN_LOCK = Lock()


class RedactingStream:
    """A file-like wrapper that redacts secrets before writing output."""

    def __init__(self, console, original_stream):
        """
        Initialize the redacting stream.

        Args:
            console: The SecretRedactorConsole to use for redaction
            original_stream: The original stream to write to
        """
        self.original_stream = original_stream
        self.encoding = getattr(original_stream, "encoding", "utf-8") or "utf-8"
        self._replacements = tuple(console._redaction_replacements())
        self._pending = [""] * len(self._replacements)

    def _redact(self, text: str, final: bool = False) -> str:
        """Stream each longest-first replacement without exposing partial matches."""
        for index, (value, replacement) in enumerate(self._replacements):
            text = self._pending[index] + text
            parts = []
            start = 0
            while (position := text.find(value, start)) != -1:
                parts.extend((text[start:position], replacement))
                start = position + len(value)

            tail = text[start:]
            pending_length = 0
            if not final:
                for length in range(min(len(tail), len(value) - 1), 0, -1):
                    if value.startswith(tail[-length:]):
                        pending_length = length
                        break
            boundary = len(tail) - pending_length
            self._pending[index] = tail[boundary:]
            parts.append(tail[:boundary])
            text = "".join(parts)
        return text

    def write(self, text: str) -> int:
        """Accept text, retaining only suffixes that might complete a secret."""
        if not text:
            return 0
        redacted_text = self._redact(text)
        if redacted_text:
            self.original_stream.write(redacted_text)
        return len(text)

    def finish(self) -> None:
        """Drain pending output at EOF without closing the caller's stream."""
        text = self._redact("", final=True)
        if text:
            self.original_stream.write(text)
        self.flush()

    def flush(self) -> None:
        """Flush emitted output, keeping possible secret prefixes until EOF."""
        if hasattr(self.original_stream, "flush"):
            self.original_stream.flush()

    def isatty(self) -> bool:
        """Return whether the stream is a tty."""
        if hasattr(self.original_stream, "isatty"):
            return self.original_stream.isatty()
        return False

    def __getattr__(self, name):
        """Delegate other attributes to the original stream."""
        return getattr(self.original_stream, name)


class OutputCapturingStream:
    """A file-like wrapper that captures output lines and feeds them to a StatusHelper."""

    def __init__(self, status_helper: "StatusHelper", original_stream):
        self._status_helper = status_helper
        self.original_stream = original_stream
        self.encoding = getattr(original_stream, "encoding", "utf-8") or "utf-8"
        self._buffer = ""

    def write(self, text: str) -> int:
        """Write text, splitting into lines for capture."""
        if not text:
            return 0

        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._status_helper.capture_line(line)

        return len(text)

    def flush(self) -> None:
        """Flush remaining buffer content."""
        if self._buffer:
            self._status_helper.capture_line(self._buffer)
            self._buffer = ""
        if hasattr(self.original_stream, "flush"):
            self.original_stream.flush()

    def isatty(self) -> bool:
        """Return whether the underlying stream is a tty."""
        if hasattr(self.original_stream, "isatty"):
            return self.original_stream.isatty()
        return False

    def __getattr__(self, name):
        """Delegate other attributes to the original stream."""
        return getattr(self.original_stream, name)


class NoStdoutRunner(Local):
    """Invoke runner with output handling and safe POSIX stdin probing."""

    def read_our_stdin(self, input_: IO) -> str | None:
        """Read stdin without Invoke's undersized POSIX ioctl buffer."""
        if not ready_for_reading(input_):
            return None

        bytes_to_read = 1
        if sys.platform != "win32" and isatty(input_) and has_fileno(input_):
            buffer = array.array("i", [0])
            try:
                fcntl.ioctl(input_, termios.FIONREAD, buffer, True)
                bytes_to_read = max(buffer[0], 1)
            except OSError:
                pass

        try:
            bytes_ = input_.read(bytes_to_read)
        except OSError as e:
            if e.errno != errno.EBADF:
                raise
            bytes_ = None
        if bytes_ and isinstance(bytes_, bytes):
            bytes_ = self.decode(bytes_)
        return bytes_

    def handle_stdin(self, input_: IO, output: IO, echo: bool = False) -> None:
        """Forward PTY input without translating carriage returns to newlines."""
        preserve_carriage_returns = (
            sys.platform != "win32"
            and self.using_pty
            and isatty(input_)
            and has_fileno(input_)
            and stdin_is_foregrounded_tty(input_)
        )
        if not preserve_carriage_returns:
            super().handle_stdin(input_, output, echo)
            return

        with _PTY_STDIN_LOCK:
            original_settings = termios.tcgetattr(input_)
            forwarding_settings = original_settings.copy()
            forwarding_settings[0] &= ~termios.ICRNL
            termios.tcsetattr(input_, termios.TCSANOW, forwarding_settings)
            try:
                super().handle_stdin(input_, output, echo)
            finally:
                termios.tcsetattr(input_, termios.TCSADRAIN, original_settings)

    def echo(self, command):
        if hasattr(self.context, "print"):
            # Safety first
            syn = Syntax(command, "bash")
            self.context.print(syn)
        else:
            debug("context is missing print")
            print(self.opts["echo_format"].format(command=command), file=sys.stderr)

    def _get_status_helper(self) -> "StatusHelper | None":
        if hasattr(self.context, "_status_helper"):
            return self.context._status_helper  # pylint: disable=protected-access
        return None

    def _handle_output(self, buffer_, hide, output, reader):
        """Finish redaction when a process stream ends, including async runs."""
        try:
            super()._handle_output(buffer_, hide, output, reader)
        finally:
            if isinstance(output, RedactingStream):
                output.finish()

    def run(self, command, **kwargs):
        """Execute command with redacting streams and optional output capture."""
        # Capture first so redaction also protects verbose status output.
        status_helper = self._get_status_helper()
        if status_helper and status_helper.is_verbose:
            out_stream = kwargs.get("out_stream") or sys.stdout
            err_stream = kwargs.get("err_stream") or sys.stderr
            kwargs["out_stream"] = OutputCapturingStream(status_helper, out_stream)
            kwargs["err_stream"] = OutputCapturingStream(status_helper, err_stream)
            kwargs["hide"] = False

        # Get the configured console objects
        out_console = get_console("out")
        err_console = get_console("err")

        # Check if redaction is enabled on any stream
        has_out_redaction = bool(out_console.secret_patterns)
        has_err_redaction = bool(err_console.secret_patterns)

        # If redaction is enabled, wrap the streams
        if has_out_redaction or has_err_redaction:
            # Get the output streams from kwargs or use defaults
            out_stream = kwargs.get("out_stream") or sys.stdout
            err_stream = kwargs.get("err_stream") or sys.stderr

            # Wrap streams with redacting wrappers
            if has_out_redaction:
                kwargs["out_stream"] = RedactingStream(out_console, out_stream)

            if has_err_redaction:
                kwargs["err_stream"] = RedactingStream(err_console, err_stream)

            debug(
                f"Running with redacting streams: {has_out_redaction=}, {has_err_redaction=}"
            )

        return super().run(command, **kwargs)
