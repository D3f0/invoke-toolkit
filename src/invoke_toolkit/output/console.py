"""
Rich console instance
"""

import os
import re
from fnmatch import fnmatch
from typing import List, Literal, Pattern, Union
from typing_extensions import Annotated
from invoke.util import debug

from rich.console import Console
from rich.text import Text
from invoke_toolkit.utils.singleton import singleton


class SecretScrubberConsole(Console):
    """Console that automatically scrubs secret values from output."""

    def __init__(
        self,
        *args,
        secret_patterns: Union[List[str], None] = None,
        substitution: Annotated[
            str, "The substitution can be a single character or a f-template string"
        ] = "${}",
        **kwargs,
    ):
        """
        Initialize console with secret scrubbing.

        Args:
            secret_patterns: List of patterns to match secret keys.
                            Supports: simple strings, fnmatch patterns, or regex.
                            If None, uses all environment variables.
            scrub_char: Character to replace secrets with (default: "*")
        """
        super().__init__(*args, **kwargs)
        self._compiled_patterns: List[Pattern] = []
        self._secret_map: dict = {}
        self.secret_patterns = secret_patterns or []
        self.substitution = substitution

    _secret_patterns: list[str]

    @property
    def secret_patterns(self) -> List[str]:
        """Getter for secret_patterns"""
        return self._secret_patterns

    @secret_patterns.setter
    def secret_patterns(self, value: list[str]) -> None:
        """Setter for secret_patterns"""
        self._secret_patterns = value
        self._initialize_secrets(self._secret_patterns)

    def _initialize_secrets(self, patterns: Union[List[str], None]) -> None:
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
                self._compiled_patterns.append(pattern)

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

    def _scrub_text(self, text: str) -> str:
        """Replace secret values with scrubbed version."""
        scrubbed = text

        # Sort by length (longest first) to avoid partial replacements
        sorted_secrets = sorted(
            self._secret_map.items(), key=lambda x: len(x[1]), reverse=True
        )

        for key, value in sorted_secrets:
            if value:  # Skip empty values
                # Create scrubbed replacement (same length as secret)
                if len(self.substitution) == 1:
                    scrubbed_value = self.substitution * len(value)
                else:
                    scrubbed_value = self.substitution.format(key)
                scrubbed = scrubbed.replace(value, scrubbed_value)

        return scrubbed

    def print(self, *objects, **kwargs):
        """Override print to scrub secrets before output."""
        # Process each object
        scrubbed_objects = []

        for obj in objects:
            if isinstance(obj, str):
                scrubbed_objects.append(self._scrub_text(obj))
            elif isinstance(obj, Text):
                # Rebuild Text object with scrubbed content
                new_text = Text()

                for segment in obj._spans:  # pylint: disable=protected-access
                    start, end, style = segment
                    segment_text = obj.plain[start:end]
                    scrubbed_segment = self._scrub_text(segment_text)
                    new_text.append(scrubbed_segment, style=style)

                scrubbed_objects.append(new_text)
            else:
                scrubbed_objects.append(obj)

        super().print(*scrubbed_objects, **kwargs)

    def __repr__(self) -> str:
        return (
            f"<console with secret scrubbing width={self.width}"
            f" {self._color_system!s} {self.secret_patterns}>"
        )


@singleton
class ConsoleManager:  # pylint: disable=too-few-public-methods
    """Manages console instantiation"""

    def __init__(self):
        self._consoles: dict[str, Console] = {}

    def get_console(
        self,
        stream: Union[Literal["out"], Literal["err"], Literal["log"]] = "err",
    ) -> Union[SecretScrubberConsole]:
        """
        Returns a Console object. If scrub is on will return a SecretScrubberConsole

        The streams are cached, so you don't need to pass the scrub or patterns arguments
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

            self._consoles[stream] = SecretScrubberConsole(**kwargs)
        else:
            debug(
                f"Providing exiting console for  {stream=} {self._consoles[stream]=} "
                f"{type(self._consoles[stream])=}"
            )

        return self._consoles[stream]


manager = ConsoleManager()

get_console = manager.get_console
