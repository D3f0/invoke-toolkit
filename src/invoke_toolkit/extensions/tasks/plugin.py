"""Internal tasks for managing uv-installed invoke-toolkit plugins."""

import shlex
from pathlib import Path
from typing import Annotated

from invoke_toolkit import Context, task
from invoke_toolkit.extensions.uv_tools import (
    AmbiguousPluginError,
    Plugin,
    PluginNotFoundError,
    ReceiptError,
    ToolReceipt,
    UvTool,
    active_tool,
    add_args,
    installed_plugins,
    link_args,
    load_receipt,
    remove_args,
    resolve_plugin,
    run_uv,
    update_plan,
)


def _active_state(ctx: Context) -> tuple[UvTool, ToolReceipt]:
    tool = active_tool()
    if tool is None:
        ctx.rich_exit(
            "Could not detect an active uv tool installation for invoke-toolkit. "
            "Run this command from a persistent uv tool, not uvx, uv run, or a "
            "project environment."
        )
    assert tool is not None
    try:
        receipt = load_receipt(tool)
    except ReceiptError as error:
        ctx.rich_exit(str(error))
    return tool, receipt


def _plugin_state(
    ctx: Context,
) -> tuple[UvTool, ToolReceipt, tuple[Plugin, ...]]:
    tool, receipt = _active_state(ctx)
    return tool, receipt, installed_plugins(receipt)


def _run_or_exit(ctx: Context, args: list[str]) -> None:
    ctx.print(f"Running: {shlex.join(args)}")
    exit_code = run_uv(args)
    if exit_code:
        ctx.rich_exit("uv tool install failed", exit_code=exit_code)


def _print_plugin(ctx: Context, plugin: Plugin) -> None:
    version = f" v{plugin.version}" if plugin.version else " (version unavailable)"
    entry_points = ", ".join(plugin.entry_points)
    if plugin.requirement is None:
        source = "source unavailable"
    else:
        source = f"{plugin.requirement.source.value}: {plugin.requirement.value}"
        if plugin.requirement.editable:
            source += "; editable"
    ctx.print(f"- {plugin.name}{version} [{entry_points}] ({source})")


def _resolve_or_exit(ctx: Context, plugins: tuple[Plugin, ...], name: str) -> Plugin:
    try:
        return resolve_plugin(plugins, name)
    except (PluginNotFoundError, AmbiguousPluginError) as error:
        ctx.rich_exit(str(error))
    raise AssertionError("rich_exit must terminate execution")


def _complete_plugin_names(ctx: Context, incomplete: str = "") -> list[str]:
    """Complete directly installed plugin distribution names."""
    try:
        _, _, plugins = _plugin_state(ctx)
    except (ReceiptError, AssertionError, SystemExit):
        return []
    return sorted(
        plugin.name
        for plugin in plugins
        if plugin.requirement is not None and plugin.name.startswith(incomplete)
    )


@task(name="list", autoprint=False)
def list_(ctx: Context) -> None:
    """List plugins installed with the active uv-managed invoke-toolkit."""
    tool = active_tool()
    if tool is None:
        ctx.rich_exit(
            "Could not detect an active uv tool installation for invoke-toolkit. "
            "Run this command from a persistent uv tool, not uvx, uv run, or a "
            "project environment."
        )
    assert tool is not None
    try:
        receipt = load_receipt(tool)
    except ReceiptError:
        receipt = None
    plugins = installed_plugins(receipt)
    ctx.print(f"invoke-toolkit v{tool.version or 'unknown'} (uv tool)")
    if not plugins:
        ctx.print("No invoke-toolkit plugins detected.")
        return
    ctx.print("Installed plugins:")
    for installed in plugins:
        _print_plugin(ctx, installed)


@task(name="add", positional=["source"])
def add(
    ctx: Context,
    source: Annotated[str, "Package requirement, URL, or static local path"],
) -> None:
    """Add a non-editable plugin requirement to the active uv tool."""
    _, receipt = _active_state(ctx)
    try:
        args = add_args(receipt, source)
    except ValueError as error:
        ctx.rich_exit(str(error))
    _run_or_exit(ctx, args)


@task(positional=["path"])
def link(
    ctx: Context,
    path: Annotated[Path, "Local plugin directory to install as editable"],
) -> None:
    """Link an editable local plugin into the active uv tool."""
    _, receipt = _active_state(ctx)
    try:
        args = link_args(receipt, path)
    except ValueError as error:
        ctx.rich_exit(str(error))
    _run_or_exit(ctx, args)


@task(positional=["name"])
def remove(
    ctx: Context,
    name: Annotated[
        str, "Plugin distribution or entry-point name", _complete_plugin_names
    ],
) -> None:
    """Remove one directly installed plugin from the active uv tool."""
    _, receipt, plugins = _plugin_state(ctx)
    selected = _resolve_or_exit(ctx, plugins, name)
    try:
        args = remove_args(receipt, selected)
    except ReceiptError as error:
        ctx.rich_exit(str(error))
    _run_or_exit(ctx, args)


@task(positional=["name"])
def update(
    ctx: Context,
    name: Annotated[
        str, "Plugin distribution or entry-point name", _complete_plugin_names
    ] = "",
) -> None:
    """Update one plugin, or every non-editable plugin when NAME is omitted."""
    _, receipt, plugins = _plugin_state(ctx)
    try:
        plan = update_plan(receipt, plugins, name or None)
    except (PluginNotFoundError, AmbiguousPluginError, ReceiptError) as error:
        ctx.rich_exit(str(error))
    for skipped in plan.skipped:
        ctx.print(f"Skipped editable plugin: {skipped.name}")
    if plan.args is None:
        return
    _run_or_exit(ctx, plan.args)
