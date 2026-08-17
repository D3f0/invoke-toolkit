"""
Rich console instance
"""

# pylint: disable=ungrouped-imports
import os
import re
from fnmatch import fnmatch
from re import Pattern
from typing import Annotated, Any, Literal

from invoke.util import debug
from rich.console import Console, JustifyMethod, OverflowMethod
from rich.style import Style
from invoke_toolkit.utils.singleton import singleton
from rich.text import Text


class SecretRedactorConsole(Console):
    """Console that automatically redacts secret values from output."""

    def __init__(
        self,
        *args,
        secret_patterns: list[str] | None = None,
        substitution: Annotated[
            str, "The substitution can be a single character or a f-template string"
        ] = "${}",
        **kwargs,
    ):
        """
        Initialize console with secret redactbing.

        Args:
            secret_patterns: List of patterns to match secret keys.
                            Supports: simple strings, fnmatch patterns, or regex.
                            If None, uses all environment variables.
            redact_char: Character to replace secrets with (default: "*")
        """
        super().__init__(*args, **kwargs)
        self._compiled_patterns: list[Pattern[str] | str] = []
        self._secret_map: dict = {}
        self.secret_patterns = secret_patterns or []
        self.substitution = substitution

    _secret_patterns: list[str]

    @property
    def secret_patterns(self) -> list[str]:
        """Getter for secret_patterns"""
        return self._secret_patterns

    @secret_patterns.setter
    def secret_patterns(self, value: list[str]) -> None:
        """Setter for secret_patterns"""
        self._secret_patterns = value
        self._initialize_secrets(self._secret_patterns)

    def _initialize_secrets(self, patterns: list[str] | None) -> None:
        """
        Initialize secret patterns and build secret map.
        The environment variable values are sampled here.
        """
        if patterns is None:
            # Use all environment variables
            patterns = []

        for pattern in patterns:
            # Try to compile as regex first
            try:
                self._compiled_patterns.append(re.compile(pattern))
            except re.error:
                # Not a regex, treat as fnmatch pattern
                self._compiled_patterns.append(pattern)  # type: ignore[arg-type]

        # Build secret map: key -> value
        self._build_secret_map()
        debug(f"{self._secret_map=}")

    def _build_secret_map(self) -> None:
        """Build mapping of secret keys to their values."""
        self._secret_map = {}

        for key, value in os.environ.items():
            if self._matches_any_pattern(key):
                self._secret_map[key] = str(value)

    def _matches_any_pattern(self, key: str) -> bool:
        """Check if key matches any of the configured patterns."""
        for pattern in self._compiled_patterns:
            if isinstance(pattern, Pattern):
                # It's a compiled regex
                if pattern.search(key):
                    return True
            else:
                # It's a fnmatch pattern
                if fnmatch(key, pattern):
                    return True
        return False

    def _redact_text(self, text: str) -> str:
        """Replace secret values with redacted version."""
        redacted = text

        # Sort by length (longest first) to avoid partial replacements
        sorted_secrets = sorted(
            self._secret_map.items(), key=lambda x: len(x[1]), reverse=True
        )

        for key, value in sorted_secrets:
            if value:  # Skip empty values
                # Create redacted replacement (same length as secret)
                if len(self.substitution) == 1:
                    redacted_value = self.substitution * len(value)
                else:
                    redacted_value = self.substitution.format(key)
                redacted = redacted.replace(value, redacted_value)

        return redacted

    def redact(self, text: str) -> str:
        """Public method to redact text using configured secret patterns."""
        return self._redact_text(text)

    # pylint: disable=too-many-arguments,too-many-locals
    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: str | Style | None = None,
        justify: JustifyMethod | None = None,
        overflow: OverflowMethod | None = None,
        no_wrap: bool | None = None,
        emoji: bool | None = None,
        markup: bool | None = None,
        highlight: bool | None = None,
        width: int | None = None,
        height: int | None = None,
        crop: bool = True,
        soft_wrap: bool | None = None,
        new_line_start: bool = False,
    ) -> None:
        """Override print to redact secrets before output."""
        # Process each object
        redacted_objects = []

        for obj in objects:
            if isinstance(obj, str):
                redacted_objects.append(self._redact_text(obj))
            elif isinstance(obj, Text):
                # Rebuild Text object with redacted content
                new_text = Text()

                for segment in obj._spans:  # pylint: disable=protected-access
                    start, seg_end, seg_style = segment
                    segment_text = obj.plain[start:seg_end]
                    redacted_segment = self._redact_text(segment_text)
                    new_text.append(redacted_segment, style=seg_style)

                redacted_objects.append(new_text)
            else:
                redacted_objects.append(obj)

        super().print(
            *redacted_objects,
            sep=sep,
            end=end,
            style=style,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            emoji=emoji,
            markup=markup,
            highlight=highlight,
            width=width,
            height=height,
            crop=crop,
            soft_wrap=soft_wrap,
            new_line_start=new_line_start,
        )

    def __repr__(self) -> str:
        return (
            f"<console with secret redactbing width={self.width}"
            f" {self._color_system!s} {self.secret_patterns}>"
        )


@singleton
class ConsoleManager:  # pylint: disable=too-few-public-methods
    """Manages console instantiation"""

    def __init__(self):
        self._consoles: dict[str, SecretRedactorConsole] = {}

    def get_console(
        self,
        stream: Literal["out"] | Literal["err"] | Literal["log"] = "err",
    ) -> SecretRedactorConsole:
        """
        Returns a Console object. If redact is on will return a SecretRedactorConsole

        The streams are cached, so you don't need to pass the redact or patterns arguments
        afterwards, they will have no effect.
        """

        assert stream in {"err", "out", "log"}
        if stream not in self._consoles:
            debug(f"Instantiating Console objects for {stream=}")
            # TODO: find a mechanism to extend this options, for example for capture
            kwargs = {}
            if stream in {"err", "log"}:
                kwargs["stderr"] = True
            elif stream == "out":
                kwargs["stderr"] = False

            self._consoles[stream] = SecretRedactorConsole(**kwargs)
        else:
            debug(
                f"Providing exiting console for  {stream=} {self._consoles[stream]=} "
                f"{type(self._consoles[stream])=}"
            )

        return self._consoles[stream]


manager = ConsoleManager()

get_console = manager.get_console
