"""Resolution and lifetime management for URI-valued task fields."""

from __future__ import annotations

import re
import warnings
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from typing import Any

from invoke.exceptions import Exit

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.fields import Field, FieldResolutionRequest

FIELD_RESOLVER_ENTRY_POINT = "invoke_toolkit.field_resolver"
_URI_RE = re.compile(r"^(?P<scheme>[a-z][a-z0-9+.-]*)://", re.IGNORECASE)
_warned_global_providers: set[tuple[str, str, str]] = set()


@dataclass(frozen=True)
class _ResolvedFileCleanup:
    parameter: str
    path: Path
    cleanup: str
    exception_type: str | None = None


class _TaskCleanupScope:  # pylint: disable=too-few-public-methods
    """Scope marker used to release task-lifetime resolved files."""

    def __init__(self, manager: FieldCleanupManager, start: int) -> None:
        self.manager = manager
        self.start = start


class FieldCleanupManager:
    """Own resolver-created files until their requested execution boundary."""

    def __init__(self) -> None:
        self._registrations: list[_ResolvedFileCleanup] = []
        self._references: dict[Path, int] = {}
        self._released: set[int] = set()

    def register(self, parameter: str, path: Path, cleanup: str) -> None:
        """Register a local resolver's file before subsequent validation."""
        registration = _ResolvedFileCleanup(parameter, path, cleanup)
        self._registrations.append(registration)
        self._references[path] = self._references.get(path, 0) + 1

    @contextmanager
    def task_scope(self) -> Generator[None, None, None]:
        """Release task-lifetime files created in this wrapper invocation."""
        scope = _TaskCleanupScope(self, len(self._registrations))
        failed = False
        try:
            yield
        except BaseException:
            failed = True
            raise
        finally:
            failure = self._release_task_scope(scope)
            self._handle_failure(failure, failed)

    def close_pipeline(self, failed: bool = False) -> None:
        """Release every remaining managed file in reverse registration order."""
        failure = self._release_registrations(
            range(len(self._registrations) - 1, -1, -1)
        )
        self._handle_failure(failure, failed)

    def _release_task_scope(
        self, scope: _TaskCleanupScope
    ) -> _ResolvedFileCleanup | None:
        indexes = (
            index
            for index in range(len(self._registrations) - 1, scope.start - 1, -1)
            if self._registrations[index].cleanup == "task"
        )
        return self._release_registrations(indexes)

    def _release_registrations(
        self, indexes: Iterator[int] | range
    ) -> _ResolvedFileCleanup | None:
        first_failure: _ResolvedFileCleanup | None = None
        for index in indexes:
            if index in self._released:
                continue
            registration = self._registrations[index]
            self._released.add(index)
            remaining = self._references[registration.path] - 1
            if remaining:
                self._references[registration.path] = remaining
                continue
            del self._references[registration.path]
            if not (registration.path.is_file() or registration.path.is_symlink()):
                continue
            try:
                registration.path.unlink(missing_ok=True)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                if first_failure is None:
                    first_failure = _ResolvedFileCleanup(
                        registration.parameter,
                        registration.path,
                        registration.cleanup,
                        type(exc).__name__,
                    )
        return first_failure

    @staticmethod
    def _handle_failure(
        registration: _ResolvedFileCleanup | None, failed: bool
    ) -> None:
        if registration is None:
            return
        message = (
            f"Could not clean resolved field '{registration.parameter}' "
            f"({registration.exception_type})"
        )
        if failed:
            warnings.warn(message, RuntimeWarning, stacklevel=4)
            return
        raise Exit(message, code=1)


def uri_scheme(value: Any) -> str | None:
    """Return a normalized URI scheme for string values, if present."""
    if not isinstance(value, str):
        return None
    match = _URI_RE.match(value)
    return match.group("scheme").lower() if match else None


@lru_cache(maxsize=1)
def _resolver_entry_points() -> tuple[EntryPoint, ...]:
    """Discover providers once per process in deterministic order."""
    selected = entry_points().select(group=FIELD_RESOLVER_ENTRY_POINT)
    return tuple(sorted(selected, key=lambda ep: (ep.name.lower(), ep.value)))


def reset_field_resolver_cache() -> None:
    """Clear entry-point discovery and compatibility-warning state."""
    _resolver_entry_points.cache_clear()
    _warned_global_providers.clear()


def _load_resolver(scheme: str):
    candidates = [ep for ep in _resolver_entry_points() if ep.name.lower() == scheme]
    for entry_point in candidates:
        try:
            resolver = entry_point.load()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            warnings.warn(
                f"Could not load field provider for scheme '{scheme}' "
                f"from entry point '{entry_point.name}': {type(exc).__name__}",
                RuntimeWarning,
                stacklevel=3,
            )
            continue
        if not callable(resolver):
            warnings.warn(
                f"Field provider entry point '{entry_point.name}' for scheme "
                f"'{scheme}' is not callable",
                RuntimeWarning,
                stacklevel=3,
            )
            continue
        return resolver, entry_point
    return None, None


def _validate_result(
    result: Any,
    requests: tuple[FieldResolutionRequest, ...],
    provider: str,
    scheme: str,
) -> Mapping[str, Any]:
    if not isinstance(result, Mapping):
        raise Exit(
            f"Field provider '{provider}' for scheme '{scheme}' returned a non-mapping result",
            code=1,
        )
    if not all(isinstance(key, str) for key in result):
        raise Exit(
            f"Field provider '{provider}' for scheme '{scheme}' returned non-string argument keys",
            code=1,
        )
    expected = {request.parameter for request in requests}
    actual = set(result)
    if actual != expected:
        missing = ", ".join(sorted(expected - actual)) or "none"
        unexpected = ", ".join(sorted(actual - expected)) or "none"
        raise Exit(
            f"Field provider '{provider}' for scheme '{scheme}' returned invalid "
            f"argument keys (missing: {missing}; unexpected: {unexpected})",
            code=1,
        )
    return result


def _materialize_resolver_results(
    ctx: ToolkitContext,
    result: Mapping[str, Any],
    requests: tuple[FieldResolutionRequest, ...],
    fields: Mapping[str, Any],
    provider: str,
) -> dict[str, Any]:
    """Convert resolver strings into scalar values or managed temporary files."""
    manager = getattr(ctx, "_field_cleanup", None)
    materialized = dict(result)
    for request in requests:
        value = materialized[request.parameter]
        if not isinstance(value, str):
            raise Exit(
                f"Field provider '{provider}' for scheme '{uri_scheme(request.reference)}' "
                f"returned a non-string value for argument '{request.parameter}'",
                code=1,
            )
        if request.annotation is not Path:
            continue
        field = fields[request.parameter]
        try:
            path = field.create_temporary_file(request, value)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise Exit(
                f"Field provider '{provider}' for scheme '{uri_scheme(request.reference)}' "
                f"could not create a file for argument '{request.parameter}' "
                f"({type(exc).__name__})",
                code=1,
            ) from exc
        materialized[request.parameter] = path
        if manager is not None:
            manager.register(request.parameter, path, field.cleanup)
    return materialized


def resolve_field_references(
    ctx: ToolkitContext,
    values: dict[str, Any],
    annotations: Mapping[str, Any],
    fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve URI values, grouping local callbacks by identity and globals by scheme."""
    local_batches: list[tuple[str, Any, list[FieldResolutionRequest]]] = []
    global_batches: dict[str, list[FieldResolutionRequest]] = {}
    fields = fields or {parameter: Field() for parameter in values}
    for parameter, value in values.items():
        scheme = uri_scheme(value)
        if scheme is None:
            continue
        request = FieldResolutionRequest(parameter, value, annotations.get(parameter))
        resolver = fields[parameter].resolver
        if resolver is None:
            global_batches.setdefault(scheme, []).append(request)
            continue
        for batch_scheme, batch_resolver, requests in local_batches:
            if batch_scheme == scheme and batch_resolver is resolver:
                requests.append(request)
                break
        else:
            local_batches.append((scheme, resolver, [request]))

    resolved = dict(values)
    for scheme, resolver, requests in local_batches:
        frozen_requests = tuple(requests)
        try:
            result = resolver(ctx, frozen_requests)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            parameters = ", ".join(
                sorted(request.parameter for request in frozen_requests)
            )
            raise Exit(
                f"Task-local field resolver for scheme '{scheme}' failed for arguments: "
                f"{parameters} ({type(exc).__name__})",
                code=1,
            ) from exc
        result = _validate_result(
            result, frozen_requests, "task-local resolver", scheme
        )
        resolved.update(
            _materialize_resolver_results(
                ctx, result, frozen_requests, fields, "task-local resolver"
            )
        )

    for scheme, requests in global_batches.items():
        resolver, entry_point = _load_resolver(scheme)
        if resolver is None:
            parameters = ", ".join(sorted(request.parameter for request in requests))
            warnings.warn(
                f"No field provider is installed for scheme '{scheme}' "
                f"(arguments: {parameters})",
                RuntimeWarning,
                stacklevel=3,
            )
            raise Exit(
                f"No usable field provider for scheme '{scheme}' "
                f"(arguments: {parameters})",
                code=1,
            )
        assert entry_point is not None
        warning_key = (scheme, entry_point.name, entry_point.value)
        if warning_key not in _warned_global_providers:
            _warned_global_providers.add(warning_key)
            warnings.warn(
                f"Using globally installed field provider '{entry_point.name}' for scheme "
                f"'{scheme}'; declare a task-local Field(resolver=...) instead",
                RuntimeWarning,
                stacklevel=3,
            )
        frozen_requests = tuple(requests)
        try:
            result = resolver(ctx, frozen_requests)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            parameters = ", ".join(
                sorted(request.parameter for request in frozen_requests)
            )
            raise Exit(
                f"Field provider '{entry_point.name}' for scheme '{scheme}' failed for "
                f"arguments: {parameters} ({type(exc).__name__})",
                code=1,
            ) from exc
        result = _validate_result(result, frozen_requests, entry_point.name, scheme)
        resolved.update(
            _materialize_resolver_results(
                ctx, result, frozen_requests, fields, entry_point.name
            )
        )
    return resolved
