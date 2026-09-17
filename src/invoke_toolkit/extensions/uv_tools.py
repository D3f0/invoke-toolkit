"""Inspect and manage plugins in a persistent uv tool installation."""

from __future__ import annotations

import importlib.metadata
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any

from tomlkit import loads as toml_loads

COLLECTION_ENTRY_POINT = "invoke_toolkit.collection"
TOOL_LIST_COMMAND = (
    "uv tool list --show-paths --show-with --show-version-specifiers --show-extras"
)


class ReceiptError(ValueError):
    """The active uv tool receipt cannot be safely replayed."""


class PluginNotFoundError(ValueError):
    """No installed plugin matches a requested name."""


class AmbiguousPluginError(ValueError):
    """More than one installed plugin matches a requested name."""


class RequirementSource(str, Enum):
    """Source represented by one uv receipt requirement."""

    REGISTRY = "registry"
    GIT = "git"
    URL = "url"
    DIRECTORY = "directory"
    EDITABLE = "editable"


@dataclass(frozen=True)
class UvTool:
    """A tool entry reported by ``uv tool list``."""

    name: str
    version: str | None
    environment: Path
    requirements: tuple[str, ...] = ()
    entrypoints: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ReceiptRequirement:
    """One replayable requirement from a uv tool receipt."""

    name: str
    value: str
    source: RequirementSource
    editable: bool = False

    @property
    def install_option(self) -> str:
        """Return the uv option used for a supplemental requirement."""
        return "--with-editable" if self.editable else "--with"


@dataclass(frozen=True)
class ToolReceipt:
    """The base tool requirement and all supplemental requirements."""

    base: ReceiptRequirement
    supplemental: tuple[ReceiptRequirement, ...]


@dataclass(frozen=True)
class Plugin:
    """A distribution that owns one or more toolkit collection entry points."""

    name: str
    version: str | None
    entry_points: tuple[str, ...]
    requirement: ReceiptRequirement | None


@dataclass(frozen=True)
class UpdatePlan:
    """One optional uv mutation and the plugins it affects or skips."""

    args: list[str] | None
    updated: tuple[Plugin, ...]
    skipped: tuple[Plugin, ...]


def normalize_name(name: str) -> str:
    """Normalize a Python distribution name for identity comparisons."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_tool_list(output: str) -> tuple[UvTool, ...]:
    """Parse the block-oriented output of ``uv tool list``."""
    tools: list[UvTool] = []
    current: dict[str, Any] | None = None
    header = re.compile(
        r"^(?P<name>\S+)\s+v(?P<version>\S+)"
        r"(?P<metadata>.*?)\s+\((?P<path>[^)]+)\)\s*$"
    )
    entrypoint = re.compile(r"^-\s+\S+(?:\s+\((?P<path>[^)]+)\))?\s*$")

    def finish() -> None:
        if current is None:
            return
        tools.append(
            UvTool(
                name=current["name"],
                version=current["version"],
                environment=Path(current["environment"]),
                requirements=tuple(current["requirements"]),
                entrypoints=tuple(current["entrypoints"]),
            )
        )

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("warning:"):
            continue
        match = header.match(line)
        if match:
            finish()
            requirements: list[str] = []
            for item in re.findall(r"\[([^]]+)]", match.group("metadata")):
                if item.startswith("with: "):
                    requirements.extend(
                        value.strip()
                        for value in item.removeprefix("with: ").split(",")
                    )
            current = {
                "name": match.group("name"),
                "version": match.group("version"),
                "environment": match.group("path"),
                "requirements": requirements,
                "entrypoints": [],
            }
            continue
        if current is not None:
            match = entrypoint.match(line)
            if match and match.group("path"):
                current["entrypoints"].append(Path(match.group("path")))
    finish()
    return tuple(tools)


def _inspect_uv(command: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return subprocess.CompletedProcess(command, 1, "", "")


def list_tools() -> tuple[UvTool, ...]:
    """Return tools reported by uv, or an empty tuple when uv is unavailable."""
    result = _inspect_uv(TOOL_LIST_COMMAND)
    return parse_tool_list(result.stdout + result.stderr)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.expanduser().resolve() == right.expanduser().resolve()
    except OSError:
        return os.path.abspath(left) == os.path.abspath(right)


def active_tool(tools: tuple[UvTool, ...] | None = None) -> UvTool | None:
    """Find the persistent uv tool environment containing this interpreter."""
    candidates = list_tools() if tools is None else tools
    prefix = Path(sys.prefix)
    return next(
        (tool for tool in candidates if _same_path(prefix, tool.environment)), None
    )


def _requirement_from_mapping(raw: dict[str, Any]) -> ReceiptRequirement:
    name = str(raw.get("name", ""))
    extras = raw.get("extras", [])
    suffix = f"[{','.join(str(extra) for extra in extras)}]" if extras else ""

    def direct_reference(value: str, *, local: bool = False) -> str:
        if not suffix:
            return value
        target = Path(value).as_uri() if local else value
        return f"{name}{suffix} @ {target}"

    if raw.get("editable"):
        value = str(raw["editable"])
        return ReceiptRequirement(
            name,
            direct_reference(value, local=True),
            RequirementSource.EDITABLE,
            editable=True,
        )
    if raw.get("directory"):
        value = str(raw["directory"])
        return ReceiptRequirement(
            name, direct_reference(value, local=True), RequirementSource.DIRECTORY
        )
    if raw.get("git"):
        value = str(raw["git"])
        if not value.startswith("git+"):
            value = f"git+{value}"
        if raw.get("rev"):
            value = f"{value}@{raw['rev']}"
        return ReceiptRequirement(name, direct_reference(value), RequirementSource.GIT)
    if raw.get("path"):
        value = str(raw["path"])
        return ReceiptRequirement(
            name, direct_reference(value, local=True), RequirementSource.DIRECTORY
        )
    if raw.get("url"):
        value = str(raw["url"])
        return ReceiptRequirement(name, direct_reference(value), RequirementSource.URL)
    return ReceiptRequirement(
        name,
        f"{name}{suffix}{raw.get('specifier', '')}",
        RequirementSource.REGISTRY,
    )


def load_receipt(tool: UvTool) -> ToolReceipt:
    """Load a uv receipt, rejecting state that cannot be replayed safely."""
    path = tool.environment / "uv-receipt.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReceiptError(f"Could not read uv tool receipt: {path}") from error
    try:
        receipt = toml_loads(text)
    except (TypeError, ValueError) as error:
        raise ReceiptError(f"Could not parse uv tool receipt: {path}") from error
    raw_requirements = receipt.get("tool", {}).get("requirements", [])
    if not isinstance(raw_requirements, list) or not raw_requirements:
        raise ReceiptError("uv tool receipt does not contain requirements")
    requirements: list[ReceiptRequirement] = []
    for raw in raw_requirements:
        if isinstance(raw, str):
            requirements.append(
                ReceiptRequirement(raw, raw, RequirementSource.REGISTRY)
            )
        elif isinstance(raw, dict):
            requirements.append(_requirement_from_mapping(dict(raw)))
        else:
            raise ReceiptError("uv tool receipt contains an invalid requirement")
    base_indexes = [
        index
        for index, requirement in enumerate(requirements)
        if normalize_name(requirement.name) == normalize_name(tool.name)
    ]
    if len(base_indexes) != 1:
        raise ReceiptError("uv tool receipt must contain exactly one base requirement")
    base_index = base_indexes[0]
    return ToolReceipt(
        requirements[base_index],
        tuple(
            requirement
            for index, requirement in enumerate(requirements)
            if index != base_index
        ),
    )


def install_args(
    receipt: ToolReceipt,
    *,
    upgrade: tuple[str, ...] = (),
    reinstall: tuple[str, ...] = (),
) -> list[str]:
    """Serialize a complete tool receipt into a deterministic uv invocation."""
    args = ["uv", "tool", "install", "--force"]
    for requirement in receipt.supplemental:
        args.extend([requirement.install_option, requirement.value])
    for name in upgrade:
        args.extend(["--upgrade-package", name])
    for name in reinstall:
        args.extend(["--reinstall-package", name])
    if receipt.base.editable:
        args.extend(["--editable", receipt.base.value])
    else:
        args.append(receipt.base.value)
    return args


def installed_plugins(receipt: ToolReceipt | None = None) -> tuple[Plugin, ...]:
    """Discover plugins from collection entry-point ownership."""
    requirements = (
        {normalize_name(item.name): item for item in receipt.supplemental}
        if receipt
        else {}
    )
    grouped: dict[str, dict[str, Any]] = {}
    entry_points = importlib.metadata.entry_points().select(
        group=COLLECTION_ENTRY_POINT
    )
    for entry_point in entry_points:
        distribution = getattr(entry_point, "dist", None)
        if distribution is None:
            continue
        name = str(distribution.metadata.get("Name", ""))
        if not name:
            continue
        key = normalize_name(name)
        item = grouped.setdefault(
            key,
            {
                "name": name,
                "version": distribution.version or None,
                "entry_points": set(),
            },
        )
        item["entry_points"].add(entry_point.name)
    return tuple(
        Plugin(
            item["name"],
            item["version"],
            tuple(sorted(item["entry_points"])),
            requirements.get(key),
        )
        for key, item in sorted(grouped.items())
    )


def resolve_plugin(plugins: Iterable[Plugin], requested: str) -> Plugin:
    """Resolve a distribution or entry-point name to exactly one plugin."""
    normalized = normalize_name(requested)
    matches = [
        plugin
        for plugin in plugins
        if normalize_name(plugin.name) == normalized
        or any(normalize_name(name) == normalized for name in plugin.entry_points)
    ]
    if not matches:
        raise PluginNotFoundError(f"Plugin not found: {requested}")
    if len(matches) > 1:
        names = ", ".join(plugin.name for plugin in matches)
        raise AmbiguousPluginError(f"Plugin name {requested!r} matches: {names}")
    return matches[0]


def add_args(receipt: ToolReceipt, source: str) -> list[str]:
    """Append one static supplemental requirement."""
    source = source.strip()
    if not source:
        raise ValueError("Plugin source must not be empty")
    requirement = ReceiptRequirement(source, source, RequirementSource.URL)
    return install_args(
        replace(receipt, supplemental=(*receipt.supplemental, requirement))
    )


def link_args(receipt: ToolReceipt, path: Path) -> list[str]:
    """Append one editable local supplemental requirement."""
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Editable plugin path must be an existing directory: {path}")
    requirement = ReceiptRequirement(
        resolved.name, str(resolved), RequirementSource.EDITABLE, editable=True
    )
    return install_args(
        replace(receipt, supplemental=(*receipt.supplemental, requirement))
    )


def _require_direct(plugin: Plugin) -> ReceiptRequirement:
    if plugin.requirement is None:
        raise ReceiptError(
            f"Plugin {plugin.name} is not a direct supplemental requirement"
        )
    return plugin.requirement


def remove_args(receipt: ToolReceipt, plugin: Plugin) -> list[str]:
    """Remove exactly one directly installed plugin requirement."""
    requirement = _require_direct(plugin)
    remaining = tuple(
        item
        for item in receipt.supplemental
        if normalize_name(item.name) != normalize_name(requirement.name)
    )
    return install_args(replace(receipt, supplemental=remaining))


def update_plan(
    receipt: ToolReceipt,
    plugins: tuple[Plugin, ...],
    requested: str | None = None,
) -> UpdatePlan:
    """Plan refreshes for one plugin or every directly installed plugin."""
    selected = (resolve_plugin(plugins, requested),) if requested else plugins
    direct = tuple(plugin for plugin in selected if plugin.requirement is not None)
    if requested and not direct:
        _require_direct(selected[0])
    skipped = tuple(
        plugin
        for plugin in direct
        if plugin.requirement and plugin.requirement.editable
    )
    updated = tuple(plugin for plugin in direct if plugin not in skipped)
    if not updated:
        return UpdatePlan(None, (), skipped)
    names = tuple(plugin.name for plugin in updated)
    return UpdatePlan(
        install_args(receipt, upgrade=names, reinstall=names), updated, skipped
    )


def run_uv(args: Sequence[str]) -> int:
    """Run uv with inherited streams and return its exit status."""
    return subprocess.run(list(args), check=False).returncode
