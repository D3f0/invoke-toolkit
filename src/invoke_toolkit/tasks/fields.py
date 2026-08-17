"""Deferred, typed defaults for invoke-toolkit task parameters."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkstemp
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeGuard, TypeVar

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
class Field:
    """Deferred task default, optionally bound to a local URI resolver."""

    default: Any = UNSET
    default_factory: Callable[["ToolkitContext"], Any] | _Unset = UNSET
    resolver: FieldResolver | None = None
    cleanup: Literal["pipeline", "task"] = "pipeline"

    def __post_init__(self) -> None:
        if self.default is not UNSET and self.default_factory is not UNSET:
            raise TypeError("Field accepts either default or default_factory, not both")
        if self.default_factory is not UNSET and not callable(self.default_factory):
            raise TypeError("Field default_factory must be callable")
        if self.resolver is not None and not callable(self.resolver):
            raise TypeError("Field resolver must be callable")
        if self.cleanup not in ("pipeline", "task"):
            raise ValueError("Field cleanup must be 'pipeline' or 'task'")

    @property
    def required(self) -> bool:
        """Whether this field has no deferred default."""
        return self.default is UNSET and self.default_factory is UNSET

    def __call__(
        self,
        *,
        default: Any = UNSET,
        default_factory: Callable[["ToolkitContext"], Any] | _Unset = UNSET,
        cleanup: Literal["pipeline", "task"] | None = None,
    ) -> "Field":
        """Bind a default to a resolver template exactly once."""
        if not self.required:
            raise TypeError("A Field with a default cannot be called")
        return type(self)(
            default=default,
            default_factory=default_factory,
            resolver=self.resolver,
            cleanup=self.cleanup if cleanup is None else cleanup,
        )

    def create_temporary_file(
        self, request: "FieldResolutionRequest", value: str
    ) -> Path:
        """Materialize a resolved string for a Path-annotated field.

        Subclasses may override this to customize filename, encoding, or storage.
        """
        descriptor, name = mkstemp(
            prefix=f"invoke-toolkit-{request.parameter}-", text=True
        )
        with open(descriptor, "w", encoding="utf-8", closefd=True) as file:
            file.write(value)
        return Path(name)


# Private internal name retained for consumers that need the concrete marker type.
_Field = Field


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
    """Provider interface for resolving one URI scheme to text in one batch."""

    def __call__(
        self,
        ctx: "ToolkitContext",
        requests: Sequence[FieldResolutionRequest],
    ) -> Mapping[str, str]: ...


def is_field(value: Any) -> TypeGuard[Field]:
    """Return whether *value* is a runtime Field marker."""
    return isinstance(value, Field)
