"""
Type annotations for finding out what's there in ctx.attribute
"""

from typing import Any, Optional, Union

from rich.console import JustifyMethod, OverflowMethod, Style
from typing_extensions import Protocol


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
