"""
Rich console instance
"""

from typing import Literal, Union

from rich.console import Console

_console: dict[str, Console] = {}


def get_console(stream: Union[Literal["out"], Literal["err"]] = "err") -> "Console":
    """Returns the console"""

    assert stream in {"err", "out"}
    if stream not in _console:
        # TODO: find a mechanism to extend this options
        kwargs = {}
        if stream == "err":
            kwargs["stderr"] = True
        elif stream == "out":
            kwargs["stderr"] = False

        _console[stream] = Console(**kwargs)

    return _console[stream]
