"""Utilities for inspecting and managing uv-installed invoke-toolkit tools."""

from __future__ import annotations

import importlib.metadata
import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from tomlkit import loads as toml_loads

from invoke_toolkit.loader.entrypoint import PLUGIN_PREFIX

TOOL_NAME = "invoke-toolkit"
TOOL_LIST_COMMAND = (
    "uv tool list --show-paths --show-with --show-version-specifiers --show-extras"
)


@dataclass(frozen=True)
class UvTool:
    """A tool entry reported by ``uv tool list``."""

    name: str
    version: str | None
    environment: Path
    requirements: tuple[str, ...] = ()
    entrypoints: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Plugin:
    """An invoke-toolkit plugin installed in the active Python environment."""

    name: str
    version: str | None
    editable_path: Path | None = None

    @property
    def short_name(self) -> str:
        """Return the generated plugin name without its standard prefix."""
        return self.name.removeprefix(PLUGIN_PREFIX)

    @property
    def requirement(self) -> str:
        """Return a conservative registry requirement for the plugin."""
        if self.version:
            return f"{self.name}=={self.version}"
        return self.name


@dataclass(frozen=True)
class ReceiptRequirement:
    """One requirement recorded in uv's tool receipt."""

    name: str
    value: str
    option: str | None = None


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
        """Append the current parsed tool, if one is active."""
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
            requirements = []
            for item in re.findall(r"\[([^]]+)\]", match.group("metadata")):
                if item.startswith("with: "):
                    requirements.extend(
                        requirement.strip()
                        for requirement in item.removeprefix("with: ").split(",")
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


def _run(command: str) -> subprocess.CompletedProcess[str]:
    """Run a uv inspection command without raising for unavailable uv."""
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
    result = _run(TOOL_LIST_COMMAND)
    return parse_tool_list(result.stdout + result.stderr)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.expanduser().resolve() == right.expanduser().resolve()
    except OSError:
        return os.path.abspath(left) == os.path.abspath(right)


def active_tool(tools: tuple[UvTool, ...] | None = None) -> UvTool | None:
    """Find the uv tool environment containing the running interpreter."""
    tools = list_tools() if tools is None else tools
    prefix = Path(sys.prefix)
    for tool in tools:
        if _same_path(prefix, tool.environment):
            return tool
    return None


def _receipt_path(tool: UvTool) -> Path:
    return tool.environment / "uv-receipt.toml"


def _load_receipt(tool: UvTool) -> dict[str, Any] | None:
    try:
        text = _receipt_path(tool).read_text(encoding="utf-8")
        return dict(toml_loads(text))
    except (OSError, ValueError):
        return None


def _requirement_value(requirement: dict[str, Any], name: str) -> ReceiptRequirement:
    extras = requirement.get("extras", [])
    suffix = f"[{','.join(str(extra) for extra in extras)}]" if extras else ""
    if requirement.get("editable"):
        return ReceiptRequirement(name, str(requirement["editable"]), "--with-editable")
    if requirement.get("directory"):
        return ReceiptRequirement(
            name, str(requirement["directory"]), "--with-editable"
        )
    if requirement.get("git"):
        value = str(requirement["git"])
        if not value.startswith("git+"):
            value = f"git+{value}"
        if requirement.get("rev"):
            value = f"{value}@{requirement['rev']}"
        return ReceiptRequirement(name, value, "--with")
    if requirement.get("url"):
        return ReceiptRequirement(name, str(requirement["url"]), "--with")
    return ReceiptRequirement(
        name,
        f"{name}{suffix}{requirement.get('specifier', '')}",
        None,
    )


def receipt_requirements(tool: UvTool) -> tuple[ReceiptRequirement, ...]:
    """Return all original tool and supplemental requirements from uv's receipt."""
    receipt = _load_receipt(tool)
    if not receipt:
        return (ReceiptRequirement(tool.name, tool.name),)
    raw_requirements = receipt.get("tool", {}).get("requirements", [])
    result: list[ReceiptRequirement] = []
    for raw in raw_requirements:
        if isinstance(raw, str):
            result.append(ReceiptRequirement(raw, raw))
        elif isinstance(raw, dict):
            name = str(raw.get("name", tool.name))
            result.append(_requirement_value(raw, name))
    return tuple(result) or (ReceiptRequirement(tool.name, tool.name),)


def receipt_requirement(tool: UvTool) -> str:
    """Recover the original base requirement from uv's receipt when possible."""
    return receipt_requirements(tool)[0].value


def _editable_path(distribution: importlib.metadata.Distribution) -> Path | None:
    """Return a direct editable source path when package metadata provides one."""
    try:
        direct_url = distribution.read_text("direct_url.json")
    except FileNotFoundError:
        return None
    if not direct_url:
        return None
    try:
        data = json.loads(direct_url)
    except (TypeError, ValueError):
        return None
    if data.get("dir_info", {}).get("editable") and data.get("url", "").startswith(
        "file://"
    ):
        return Path(unquote(urlparse(data["url"]).path))
    return None


def installed_plugins() -> tuple[Plugin, ...]:
    """List installed invoke-toolkit-prefixed distributions and their versions."""
    unique: dict[tuple[str, str | None, Path | None], Plugin] = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata["Name"] or ""
        if not name.lower().startswith(PLUGIN_PREFIX):
            continue
        plugin = Plugin(
            name=name,
            version=distribution.version or None,
            editable_path=_editable_path(distribution),
        )
        unique[(plugin.name.lower(), plugin.version, plugin.editable_path)] = plugin
    return tuple(sorted(unique.values(), key=lambda plugin: plugin.name.lower()))


def add_command(
    tool: UvTool,
    package: str = "",
    editable: str = "",
) -> str:
    """Build a forceful uv install preserving existing receipt requirements."""
    requirements = list(receipt_requirements(tool))
    if editable:
        requirements.append(
            ReceiptRequirement(
                package or Path(editable).name, editable, "--with-editable"
            )
        )
    else:
        requirements.append(ReceiptRequirement(package, package, "--with"))
    return _command_for_requirements(requirements)


def plugin_matches(plugin: Plugin, requested: str) -> bool:
    """Match either a full package name or its generated short name."""
    return requested.lower() in {plugin.name.lower(), plugin.short_name.lower()}


def install_arguments(plugins: tuple[Plugin, ...]) -> list[str]:
    """Build repeatable uv options for known installed plugins."""
    args: list[str] = []
    for plugin in plugins:
        if plugin.editable_path:
            args.extend(["--with-editable", str(plugin.editable_path)])
        else:
            args.extend(["--with", plugin.requirement])
    return args


def shell_quote(value: str) -> str:
    """Quote one command argument for the host shell."""
    return shlex.quote(value)


def _command_for_requirements(requirements: Iterable[ReceiptRequirement]) -> str:
    """Build a uv install command from ordered receipt requirements."""
    all_requirements = tuple(requirements)
    base, *supplemental = all_requirements
    args = ["uv", "tool", "install", "--force"]
    for requirement in supplemental:
        args.extend([requirement.option or "--with", shell_quote(requirement.value)])
    if base.option:
        args.extend(["--editable", shell_quote(base.value)])
    else:
        args.append(shell_quote(base.value))
    return " ".join(args)


def reinstall_command(
    tool: UvTool,
    plugins: tuple[Plugin, ...] | None = None,
    *,
    remove: str | None = None,
) -> str:
    """Build a forceful uv install preserving receipt requirements."""
    requirements = list(receipt_requirements(tool))
    if remove:
        requirements = [
            requirement
            for requirement in requirements
            if requirement.name.lower() != remove.lower()
        ]
    elif plugins is not None:
        requirements = [
            requirements[0],
            *(
                ReceiptRequirement(plugin.name, plugin.requirement, "--with")
                for plugin in plugins
            ),
        ]
    return _command_for_requirements(requirements)


def upgrade_command(tool: UvTool) -> str:
    """Build the native uv command for upgrading the active tool."""
    return f"uv tool upgrade {shell_quote(tool.name)}"
