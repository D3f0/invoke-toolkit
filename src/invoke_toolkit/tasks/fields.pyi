from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TypeGuard, TypeVar, overload

from invoke_toolkit.context import ToolkitContext

T = TypeVar("T")

class _Unset: ...

UNSET: _Unset

@dataclass(frozen=True)
class _Field:
    default: Any
    default_factory: Callable[[ToolkitContext], Any] | _Unset
    resolver: FieldResolver | None
    cleanup: Literal["pipeline", "task"]

    @property
    def required(self) -> bool: ...
    @overload
    def __call__(
        self, *, default: str, cleanup: Literal["pipeline", "task"] | None = ...
    ) -> Any: ...
    @overload
    def __call__(
        self, *, default: T, cleanup: Literal["pipeline", "task"] | None = ...
    ) -> T: ...
    @overload
    def __call__(
        self,
        *,
        default_factory: Callable[[ToolkitContext], T],
        cleanup: Literal["pipeline", "task"] | None = ...,
    ) -> T: ...
    def create_temporary_file(
        self, request: "FieldResolutionRequest", value: str
    ) -> Path: ...

@overload
def Field(*, default: str, cleanup: Literal["pipeline", "task"] = ...) -> Any: ...
@overload
def Field(*, default: T, cleanup: Literal["pipeline", "task"] = ...) -> T: ...
@overload
def Field(
    *,
    default_factory: Callable[[ToolkitContext], T],
    cleanup: Literal["pipeline", "task"] = ...,
) -> T: ...
@overload
def Field(
    *,
    resolver: Callable[
        [ToolkitContext, Sequence["FieldResolutionRequest"]], Mapping[str, str]
    ],
    cleanup: Literal["pipeline", "task"] = ...,
) -> _Field: ...
@overload
def Field(*, cleanup: Literal["pipeline", "task"] = ...) -> Any: ...
@dataclass(frozen=True)
class _DeferredField:
    parameter: str

@dataclass(frozen=True)
class FieldResolutionRequest:
    parameter: str
    reference: str
    annotation: Any

class FieldResolver(Protocol):
    def __call__(
        self,
        ctx: ToolkitContext,
        requests: Sequence[FieldResolutionRequest],
    ) -> Mapping[str, str]: ...

def is_field(value: Any) -> TypeGuard[_Field]: ...
