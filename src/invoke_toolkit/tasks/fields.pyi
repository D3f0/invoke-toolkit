from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, overload
from invoke_toolkit.context import ToolkitContext

T = TypeVar("T")

class _Unset: ...

UNSET: _Unset

@dataclass(frozen=True)
class _Field:
    default: Any
    default_factory: Callable[[ToolkitContext], Any] | _Unset
    @property
    def required(self) -> bool: ...

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
    ) -> Mapping[str, Any]: ...

@overload
def Field(*, default: str) -> Any: ...
@overload
def Field(*, default: T) -> T: ...
@overload
def Field(*, default_factory: Callable[[ToolkitContext], T]) -> T: ...
@overload
def Field() -> Any: ...
def is_field(value: Any) -> bool: ...
