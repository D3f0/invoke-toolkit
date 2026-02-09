"""
Extended parser with completion support.

This module provides an enhanced Argument class that supports completion callbacks
while maintaining backward compatibility with invoke's Argument.
"""

from typing import Any, Callable, Optional

from invoke.parser import Argument as InvokeArgument


class ToolkitArgument(InvokeArgument):
    """
    Extended Argument class with completion callback support.

    Extends invoke's Argument to support:
    - Completion callbacks for dynamic value completion
    - Future extensibility for other features

    Attributes:
        help: Help text for the argument
        complete: Optional callback for dynamic completion
    """

    def __init__(
        self,
        name: Optional[str] = None,
        names=(),
        kind=str,
        default: Optional[Any] = None,
        help: Optional[str] = None,
        positional: bool = False,
        optional: bool = False,
        incrementable: bool = False,
        attr_name: Optional[str] = None,
        complete: Optional[Callable[[Any, str], list[str]]] = None,
    ):
        """
        Initialize an Argument with optional completion callback.

        Args:
            name: Primary name for the argument
            names: Tuple of alternative names
            kind: Type of the argument (str, int, bool, list, etc.)
            default: Default value if not provided
            help: Help text describing the argument
            positional: Whether this is a positional argument
            optional: Whether this argument is optional
            incrementable: Whether this can be incremented (for flags)
            attr_name: Name to use for storing as attribute
            complete: Optional callback for completion. Signature:
                      (ctx: Context, incomplete: str = "") -> list[str]
        """
        # Call parent constructor
        super().__init__(
            name=name,
            names=names,
            kind=kind,
            default=default,
            help=help,
            positional=positional,
            optional=optional,
            incrementable=incrementable,
            attr_name=attr_name,
        )

        # Store completion callback
        self.complete = complete
