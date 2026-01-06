"""
Config object used for invoke attribute resolution
in tasks.
"""

import sys

from invoke.runners import Local
from invoke.util import debug
from rich.syntax import Syntax

from invoke_toolkit.output import get_console


class RedactingStream:
    """A file-like wrapper that redacts secrets before writing output."""

    def __init__(self, console, original_stream):
        """
        Initialize the redacting stream.

        Args:
            console: The SecretRedactorConsole to use for redaction
            original_stream: The original stream to write to
        """
        self.console = console
        self.original_stream = original_stream
        self.encoding = getattr(original_stream, "encoding", "utf-8") or "utf-8"

    def write(self, text: str) -> int:
        """Write text after redacting secrets."""
        if not text:
            return 0

        redacted_text = self.console.redact(text)
        return self.original_stream.write(redacted_text)

    def flush(self) -> None:
        """Flush the underlying stream."""
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


class NoStdoutRunner(Local):
    """Invoke runner that prints to stderr when invoke is used with -e/--echo
    and redacts secrets from subprocess output when redaction is enabled.
    """

    def echo(self, command):
        if hasattr(self.context, "print"):
            # Safety first
            syn = Syntax(command, "bash")
            self.context.print(syn)
        else:
            debug("context is missing print")
            print(self.opts["echo_format"].format(command=command), file=sys.stderr)

    def run(self, command, **kwargs):
        """Execute command with redacting streams if redaction is enabled."""
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
