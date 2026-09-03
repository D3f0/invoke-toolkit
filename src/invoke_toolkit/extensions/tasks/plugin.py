"""Internal tasks for managing uv-installed invoke-toolkit plugins."""

from __future__ import annotations

from typing import Annotated

from invoke_toolkit import Context, task
from invoke_toolkit.extensions.uv_tools import (
    Plugin,
    active_tool,
    add_command,
    installed_plugins,
    plugin_matches,
    reinstall_command,
    upgrade_command,
)


def _require_active_tool(ctx: Context):
    tool = active_tool()
    if tool is None:
        ctx.rich_exit(
            "Could not detect an active uv tool installation for invoke-toolkit. "
            "Run this command from an installed uv tool, not uvx or a project environment."
        )
    return tool


def _print_plugin(ctx: Context, plugin: Plugin) -> None:
    version = f" v{plugin.version}" if plugin.version else " (version unavailable)"
    source = f" [editable: {plugin.editable_path}]" if plugin.editable_path else ""
    ctx.print(f"- {plugin.name}{version}{source}")


@task(name="list", autoprint=False)
def list_(ctx: Context) -> None:
    """List plugins installed with the active uv-managed invoke-toolkit."""
    tool = _require_active_tool(ctx)
    plugins = installed_plugins()
    ctx.print(f"invoke-toolkit v{tool.version or 'unknown'} (uv tool)")
    if not plugins:
        ctx.print("No invoke-toolkit plugins detected.")
        return
    ctx.print("Installed plugins:")
    for plugin in plugins:
        _print_plugin(ctx, plugin)


@task(name="add")
def add(
    ctx: Context,
    package: Annotated[str, "Package requirement or git URL"] = "",
    editable: Annotated[
        str, "Local plugin directory to install with --with-editable"
    ] = "",
) -> None:
    """Add a registry, git, or editable plugin to the active uv tool."""
    if not package and not editable:
        ctx.rich_exit("Provide a package requirement or --editable plugin path.")
    tool = _require_active_tool(ctx)
    command = add_command(tool, package, editable)
    ctx.print(f"Running: {command}")
    ctx.run(command, pty=True)


@task()
def remove(
    ctx: Context,
    package: Annotated[str, "Plugin package or generated short name"],
) -> None:
    """Remove a plugin and reinstall the active uv tool without it."""
    tool = _require_active_tool(ctx)
    plugins = installed_plugins()
    matches = [plugin for plugin in plugins if plugin_matches(plugin, package)]
    if not matches:
        ctx.rich_exit(f"Plugin not found: {package}")
    command = reinstall_command(tool, remove=matches[0].name)
    ctx.print(f"Running: {command}")
    ctx.run(command, pty=True)


@task()
def update(ctx: Context) -> None:
    """Upgrade the base invoke-toolkit package in the active uv tool."""
    tool = _require_active_tool(ctx)
    command = upgrade_command(tool)
    ctx.print(f"Running: {command}")
    ctx.run(command, pty=True)
    ctx.print(
        "Note: supplemental plugin requirements retain their uv constraints; "
        "use plugin.add/remove to rebuild the tool requirement set."
    )


def _matches(plugin: Plugin, requested: str) -> bool:
    return requested.lower() in {plugin.name.lower(), plugin.short_name.lower()}
