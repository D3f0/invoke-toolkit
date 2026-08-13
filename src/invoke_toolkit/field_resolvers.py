"""Entry-point based resolution of URI-valued task fields."""

from __future__ import annotations

import re
import warnings
from collections import defaultdict
from collections.abc import Mapping
from functools import lru_cache
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from invoke.exceptions import Exit

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.fields import FieldResolutionRequest

FIELD_RESOLVER_ENTRY_POINT = "invoke_toolkit.field_resolver"
_URI_RE = re.compile(r"^(?P<scheme>[a-z][a-z0-9+.-]*)://", re.IGNORECASE)


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
    """Clear entry-point discovery state (primarily for isolated tests)."""
    _resolver_entry_points.cache_clear()


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


def resolve_field_references(
    ctx: ToolkitContext,
    values: dict[str, Any],
    annotations: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve URI values in one provider call per scheme.

    Unknown schemes are intentionally non-fatal: the original reference is
    retained and a warning explains that no provider was available.
    """
    batches: dict[str, list[FieldResolutionRequest]] = defaultdict(list)
    for parameter, value in values.items():
        scheme = uri_scheme(value)
        if scheme is not None:
            batches[scheme].append(
                FieldResolutionRequest(parameter, value, annotations.get(parameter))
            )

    resolved = dict(values)
    for scheme, requests in batches.items():
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

        try:
            result = resolver(ctx, tuple(requests))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            parameters = ", ".join(sorted(request.parameter for request in requests))
            raise Exit(
                f"Field provider '{entry_point.name}' for scheme '{scheme}' "
                f"failed for arguments: {parameters} ({type(exc).__name__})",
                code=1,
            ) from exc

        if not isinstance(result, Mapping):
            raise Exit(
                f"Field provider '{entry_point.name}' for scheme '{scheme}' "
                "returned a non-mapping result",
                code=1,
            )
        expected = {request.parameter for request in requests}
        if not all(isinstance(key, str) for key in result):
            raise Exit(
                f"Field provider '{entry_point.name}' for scheme '{scheme}' "
                "returned non-string argument keys",
                code=1,
            )
        actual = set(result)
        if actual != expected:
            missing = ", ".join(sorted(expected - actual)) or "none"
            unexpected = ", ".join(sorted(actual - expected)) or "none"
            raise Exit(
                f"Field provider '{entry_point.name}' for scheme '{scheme}' "
                f"returned invalid argument keys (missing: {missing}; "
                f"unexpected: {unexpected})",
                code=1,
            )
        resolved.update(result)

    return resolved
