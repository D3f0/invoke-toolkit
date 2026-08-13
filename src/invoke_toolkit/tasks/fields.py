"""Deferred, typed defaults for invoke-toolkit task parameters."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, overload

if TYPE_CHECKING:
    from invoke_toolkit.context import ToolkitContext

T = TypeVar("T")


class _Unset:
    """Private sentinel which distinguishes ``Field()`` from ``Field(None)``."""

    def __repr__(self) -> str:
        return "UNSET"

    def __copy__(self) -> "_Unset":
        return self

    def __deepcopy__(self, memo: object) -> "_Unset":
        return self


UNSET = _Unset()


@dataclass(frozen=True)
class _Field:
    """Runtime marker retained in a task function signature."""

    default: Any = UNSET
    default_factory: Callable[["ToolkitContext"], Any] | _Unset = UNSET

    @property
    def required(self) -> bool:
        """Whether this field has no deferred default."""
        return self.default is UNSET and self.default_factory is UNSET


@dataclass(frozen=True)
class _DeferredField:
    """Deepcopy-safe marker indicating that a parser value was omitted."""

    parameter: str


@dataclass(frozen=True)
class FieldResolutionRequest:
    """One deferred URI value given to a scheme provider."""

    parameter: str
    reference: str
    annotation: Any


class FieldResolver(Protocol):
    """Provider interface for resolving one URI scheme in a single batch."""

    def __call__(
        self,
        ctx: "ToolkitContext",
        requests: Sequence[FieldResolutionRequest],
    ) -> Mapping[str, Any]: ...


@overload
def Field(*, default: str) -> Any: ...


@overload
def Field(*, default: T) -> T: ...


@overload
def Field(*, default_factory: Callable[["ToolkitContext"], T]) -> T: ...


@overload
def Field() -> Any: ...


def Field(
    *,
    default: Any = UNSET,
    default_factory: Callable[["ToolkitContext"], Any] | _Unset = UNSET,
) -> Any:
    """Declare a deferred default for a task parameter.

    Type overloads intentionally make ``Field`` usable as the normal Python
    default of an annotated parameter. At runtime the returned marker is
    consumed by :func:`invoke_toolkit.task` before the task body is called.
    """
    if default is not UNSET and default_factory is not UNSET:
        raise TypeError("Field accepts either default or default_factory, not both")
    if default_factory is not UNSET and not callable(default_factory):
        raise TypeError("Field default_factory must be callable")
    return _Field(default=default, default_factory=default_factory)


def is_field(value: Any) -> bool:
    """Return whether *value* is a runtime Field marker."""
    return isinstance(value, _Field)
