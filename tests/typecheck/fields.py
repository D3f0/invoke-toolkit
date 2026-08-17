"""Positive static typing examples for Field task defaults."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated

from invoke_toolkit import Context, Field, FieldResolutionRequest, task
from invoke_toolkit.tasks.types import _FileCompletionMarker


def configured_name(ctx: Context) -> str:
    return str(ctx.config.get("name", "default"))


def configured_path(ctx: Context) -> Path:
    return Path(str(ctx.config.get("path", "config.toml")))


def resolve_bw(
    _ctx: Context, _requests: Sequence[FieldResolutionRequest]
) -> Mapping[str, str]:
    return {}


BitwardenField = Field(resolver=resolve_bw)


@task
def typed_fields(
    ctx: Context,
    name: str = Field(default="literal"),
    count: int = Field(default=3),
    dynamic_name: str = Field(default_factory=configured_name),
    dynamic_path: Path = Field(default_factory=configured_path),
    secret_file: Annotated[
        Path, _FileCompletionMarker(exists=True, dir_okay=False)
    ] = Field(default="op://Vault/config"),
    required: str = Field(),
) -> None:
    del ctx, name, count, dynamic_name, dynamic_path, secret_file, required


@task
def local_resolver_fields(
    ctx: Context,
    secret: str = BitwardenField(default="bw://SECRET"),
    config: Annotated[
        Path, _FileCompletionMarker(exists=True, dir_okay=False)
    ] = BitwardenField(default="bw://CONFIG", cleanup="task"),
) -> None:
    del ctx, secret, config
