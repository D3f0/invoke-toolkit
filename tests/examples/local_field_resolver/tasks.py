# pylint: disable=invalid-name
"""Self-contained task-local Field resolver example.

Run from the repository root:

    intk --search-root tests/examples/local_field_resolver deploy

The resolver is local to this task collection; no provider package or entry
point is required. The generated config file exists while ``deploy`` runs and
is removed when the invocation pipeline finishes.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast
from collections.abc import Mapping, Sequence

from invoke.runners import Result
from invoke_toolkit import Context, Field, FieldResolutionRequest, task


def resolve_demo_secrets(
    ctx: Context,
    requests: Sequence[FieldResolutionRequest],
) -> Mapping[str, str]:
    """Resolve text with a secret-manager CLI substituted for this demo command."""
    resolved: dict[str, str] = {}
    for request in requests:
        # Replace this with the actual password or secret-manager CLI invocation.
        result = cast(Result, ctx.run("echo secret", hide=True))
        resolved[request.parameter] = result.stdout.strip()
    return resolved


BitwardenField = Field(resolver=resolve_demo_secrets)


@task
def deploy(
    ctx: Context,
    password: str = BitwardenField(default="bw://DEPLOY_PASSWORD"),
    config: Path = BitwardenField(default="bw://DEPLOY_CONFIG"),
) -> None:
    """Use scalar and file-backed values resolved by the local Field callback."""
    del password
    ctx.print(f"Deploying with temporary config: {config.exists()}")
