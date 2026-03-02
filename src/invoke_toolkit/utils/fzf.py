"""
fzf integration utilities for interactive selection.

This module provides utilities for using fzf (fuzzy finder) to create
interactive selection interfaces in tasks. Falls back to rich-based
selection when fzf is not available.

Environment Variables:
    INVOKE_FUZZY_FINDER_FORCE_FALLBACK: Set to '1', 'true', or 'yes' to force
        the use of rich fallback instead of fzf, even when fzf is available.
        This follows invoke's standard config system where nested config keys
        like 'fuzzy_finder.force_fallback' become 'INVOKE_FUZZY_FINDER_FORCE_FALLBACK'.
"""

import subprocess
import tempfile
from pathlib import Path
from shutil import which
from typing import Any, Optional

from invoke import Context
from invoke.util import debug
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

# Track if we've shown the warning to avoid spam
_fzf_warning_shown = False


def is_fzf_available() -> bool:
    """
    Check if fzf is available in PATH.

    Returns:
        True if fzf is installed and available, False otherwise.
    """
    fzf_path = which("fzf")
    available = fzf_path is not None
    debug(f"fzf availability check: {available} (path: {fzf_path})")
    return available


def _show_fzf_warning(ctx: Context, force_fallback: bool = False) -> None:
    """
    Show a warning message when fzf is not available or disabled.

    Can be disabled via config: fuzzy_finder.show_warnings = False

    Args:
        ctx: The invoke context
        force_fallback: Whether fallback is forced via config
    """
    global _fzf_warning_shown  # pylint: disable=global-statement

    # Only show once per session
    if _fzf_warning_shown:
        debug("fzf warning already shown this session, skipping")
        return

    # Check if warnings are disabled in config
    try:
        show_warnings = ctx.config.get("fuzzy_finder", {}).get("show_warnings", True)
    except (AttributeError, KeyError):
        show_warnings = True

    if not show_warnings:
        debug("fzf warnings disabled in config")
        return

    debug("Showing fzf warning message")

    if force_fallback:
        ctx.print_err(
            "[yellow]Note:[/yellow] fzf is disabled via config (force_fallback=true). "
            "Using rich-based fallback selector."
        )
        ctx.print_err("[dim]Re-enable with: fuzzy_finder.force_fallback = false[/dim]")
    else:
        ctx.print_err(
            "[yellow]Note:[/yellow] fzf not found. "
            "For better interactive selection, install fzf: "
            "[cyan]https://github.com/junegunn/fzf[/cyan]"
        )
        ctx.print_err(
            "[dim]Disable this message with config: fuzzy_finder.show_warnings = false[/dim]"
        )

    _fzf_warning_shown = True


def _rich_select(  # pylint: disable=too-many-return-statements
    choices: list[str],
    prompt: str = "Select an option",
    multi: bool = False,
    select_1: bool = False,
    exit_0: bool = False,
) -> Optional[str | list[str]]:
    """
    Fallback selector using rich when fzf is not available.

    Args:
        choices: List of options to choose from
        prompt: Prompt message
        multi: Allow multiple selections (not supported in rich fallback)
        select_1: Automatically select if only one match
        exit_0: Exit immediately if no matches

    Returns:
        Selected item or None if cancelled
    """
    debug(
        f"_rich_select called with {len(choices)} choices, multi={multi}, select_1={select_1}, exit_0={exit_0}"
    )

    if not choices:
        debug("No choices provided, returning empty result")
        if exit_0:
            # Exit immediately if no matches and exit_0 is set
            return [] if multi else None
        return [] if multi else None

    # Automatically select if only one choice and select_1 is set
    if select_1 and len(choices) == 1:
        debug(f"select_1=True with single choice, auto-selecting: {choices[0]}")
        return [choices[0]] if multi else choices[0]

    console = Console()

    if multi:
        console.print(
            "[yellow]Note: Multi-select not available without fzf. "
            "Install fzf for full functionality.[/yellow]"
        )

    # Display choices in a table
    table = Table(title=prompt, show_header=True, header_style="bold cyan")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Option")

    for idx, choice in enumerate(choices, 1):
        table.add_row(str(idx), choice)

    console.print(table)

    # Ask for selection
    try:
        selection = Prompt.ask(
            f"[bold]{prompt}[/bold] (enter number, or 'q' to quit)",
            default="q",
        )

        if selection.lower() == "q":
            return [] if multi else None

        # Convert to index
        try:
            idx = int(selection) - 1
            if 0 <= idx < len(choices):
                result = choices[idx]
                debug(f"User selected index {idx}: {result}")
                return [result] if multi else result

            console.print(f"[red]Invalid selection: {selection}[/red]")
            debug(f"Invalid selection index: {selection}")
            return [] if multi else None
        except ValueError:
            console.print(f"[red]Invalid input: {selection}[/red]")
            debug(f"Non-numeric input received: {selection}")
            return [] if multi else None

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Selection cancelled[/yellow]")
        debug("User cancelled selection")
        return [] if multi else None


def _run_fzf(
    fzf_cmd: list[str],
    choices_content: str,
    multi: bool,
) -> Optional[str | list[str]]:
    """
    Run fzf with the given command and choices content.

    Args:
        fzf_cmd: List of fzf command arguments
        choices_content: Content to pipe to fzf
        multi: Whether multi-select is enabled

    Returns:
        Selected item(s) or None if cancelled
    """
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp.write(choices_content)
            tmp.flush()  # Ensure content is written to disk
            tmp_path = tmp.name

        # Build shell command with input redirection
        shell_cmd = f"{' '.join(fzf_cmd)} < {tmp_path}"
        debug(f"Running fzf command: {shell_cmd}")

        # Run fzf with shell mode and input redirection
        result = subprocess.run(
            shell_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # User cancelled (Ctrl-C or ESC) or error occurred
            debug(f"fzf exited with code {result.returncode}")
            return [] if multi else None

        # Parse result
        output = result.stdout.strip()
        debug(f"fzf returned: {output}")
        if not output:
            return [] if multi else None

        if multi:
            result_list = output.split("\n")
            debug(f"Returning {len(result_list)} selected items")
            return result_list
        debug(f"Returning single selected item: {output}")
        return output
    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink()
        except Exception as e:  # pylint: disable=broad-except
            debug(f"Failed to delete temp file {tmp_path}: {e}")


def select(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    ctx: Context,
    choices: list[str],
    prompt: str = "Select an option",
    multi: bool = False,
    preview: Optional[str] = None,
    preview_window: str = "right:50%",
    height: str = "40%",
    reverse: bool = True,
    use_fallback: bool = True,
    **kwargs: Any,
) -> Optional[str | list[str]]:
    """
    Use fzf to interactively select from a list of choices.

    This function pipes choices to fzf and returns the user's selection.
    Requires fzf to be installed (https://github.com/junegunn/fzf).

    Args:
        ctx: The invoke context
        choices: List of options to choose from
        prompt: Prompt message to display (default: "Select an option")
        multi: Allow multiple selections (default: False)
        preview: Preview command template using {} as placeholder for selection
        preview_window: Preview window layout (default: "right:50%")
        height: Height of fzf window (default: "40%")
        reverse: Display from top to bottom (default: True)
        use_fallback: Use rich-based fallback if fzf not available (default: True)
        **kwargs: Additional fzf options as keyword arguments

    Returns:
        Selected item (string) if multi=False, or list of selected items if multi=True.
        Returns None if user cancels selection.

    Raises:
        RuntimeError: If fzf is not installed and use_fallback=False

    Environment Variables:
        INVOKE_FUZZY_FINDER_FORCE_FALLBACK: Set to '1', 'true', or 'yes' to force
            the use of rich fallback instead of fzf. This follows invoke's standard
            config system.

    Examples:
        Basic selection:
        ```python
        from invoke_toolkit import task, Context
        from invoke_toolkit.utils.fzf import select

        @task
        def deploy(ctx: Context):
            targets = ["production", "staging", "development"]
            target = select(ctx, targets, prompt="Select deployment target")
            if target:
                ctx.run(f"./deploy.sh {target}")
        ```

        Multi-select:
        ```python
        @task
        def test_files(ctx: Context):
            import os
            test_files = [f for f in os.listdir("tests") if f.startswith("test_")]
            selected = select(
                ctx,
                test_files,
                prompt="Select test files to run",
                multi=True
            )
            if selected:
                ctx.run(f"pytest {' '.join(selected)}")
        ```

        With preview:
        ```python
        @task
        def view_logs(ctx: Context):
            logs = ctx.run("ls logs/*.log", hide=True).stdout.strip().split()
            selected = select(
                ctx,
                logs,
                prompt="Select log file",
                preview="head -50 {}",
                preview_window="right:60%"
            )
            if selected:
                ctx.run(f"less {selected}")
        ```

        With custom fzf options:
        ```python
        @task
        def select_branch(ctx: Context):
            branches = ctx.run(
                "git branch --all",
                hide=True
            ).stdout.strip().split("\n")
            branch = select(
                ctx,
                branches,
                prompt="Select branch",
                preview="git log --oneline --graph --color=always {}",
                ansi=True,  # Enable ANSI color codes
                border="rounded"  # Add rounded border
            )
            if branch:
                ctx.run(f"git checkout {branch.strip()}")
        ```
    """
    debug(
        f"select() called with {len(choices)} choices, multi={multi}, "
        f"preview={preview is not None}, use_fallback={use_fallback}"
    )

    # Check if force_fallback is enabled in config (includes environment variables)
    # Invoke's config system automatically handles INVOKE_FUZZY_FINDER_FORCE_FALLBACK
    force_fallback = ctx.config.get("fuzzy_finder", {}).get("force_fallback", False)
    debug(f"force_fallback value: {force_fallback}")

    if force_fallback:
        debug(
            "force_fallback enabled (via config or INVOKE_FUZZY_FINDER_FORCE_FALLBACK)"
        )

    # Check if fzf is available
    fzf_available = is_fzf_available() and not force_fallback

    if not fzf_available:
        if force_fallback:
            debug("force_fallback enabled in config, using rich fallback")
        else:
            debug("fzf not available, attempting fallback")

        if not use_fallback:
            raise RuntimeError(
                "fzf is not installed. Install from: https://github.com/junegunn/fzf"
            )
        # Show warning message (once per session, configurable)
        _show_fzf_warning(ctx, force_fallback=force_fallback)
        # Use rich-based fallback with select_1 and exit_0 support
        select_1 = kwargs.get("select_1", False)
        exit_0 = kwargs.get("exit_0", False)
        debug("Using rich fallback selector")
        return _rich_select(choices, prompt, multi, select_1, exit_0)

    if not choices:
        debug("No choices provided, returning empty result")
        return [] if multi else None

    # Build fzf command
    fzf_cmd = ["fzf"]
    debug("Building fzf command")

    # Add standard options
    fzf_cmd.append(f'--prompt="{prompt}: "')
    fzf_cmd.append(f"--height={height}")

    if reverse:
        fzf_cmd.append("--reverse")

    if multi:
        fzf_cmd.append("--multi")

    # Handle select-1 option (auto-select if only one match)
    if kwargs.get("select_1"):
        debug("Adding --select-1 flag")
        fzf_cmd.append("--select-1")
        kwargs.pop("select_1")  # Remove from kwargs to avoid duplication

    # Handle exit-0 option (exit immediately if no matches)
    if kwargs.get("exit_0"):
        debug("Adding --exit-0 flag")
        fzf_cmd.append("--exit-0")
        kwargs.pop("exit_0")  # Remove from kwargs to avoid duplication

    if preview:
        fzf_cmd.append(f"--preview='{preview}'")
        fzf_cmd.append(f"--preview-window={preview_window}")

    # Add custom kwargs as fzf options
    for key, value in kwargs.items():
        flag = key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                fzf_cmd.append(f"--{flag}")
        else:
            # Quote value if it contains spaces
            if isinstance(value, str) and " " in value:
                fzf_cmd.append(f"--{flag}='{value}'")
            else:
                fzf_cmd.append(f"--{flag}={value}")

    # Run fzf with choices
    return _run_fzf(fzf_cmd, "\n".join(choices), multi)


def select_from_command(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-return-statements
    ctx: Context,
    command: str,
    prompt: str = "Select an option",
    multi: bool = False,
    preview: Optional[str] = None,
    preview_window: str = "right:50%",
    height: str = "40%",
    reverse: bool = True,
    use_fallback: bool = True,
    **kwargs: Any,
) -> Optional[str | list[str]]:
    """
    Use fzf to select from the output of a command.

    This is a convenience function that runs a command, splits its output
    by lines, and passes those lines to fzf for selection.

    Args:
        ctx: The invoke context
        command: Shell command whose output will be the choices
        prompt: Prompt message to display
        multi: Allow multiple selections
        preview: Preview command template
        preview_window: Preview window layout
        height: Height of fzf window
        reverse: Display from top to bottom
        use_fallback: Use rich-based fallback if fzf not available (default: True)
        **kwargs: Additional fzf options

    Returns:
        Selected item(s) or None if cancelled

    Raises:
        RuntimeError: If fzf is not installed and use_fallback=False

    Environment Variables:
        INVOKE_FUZZY_FINDER_FORCE_FALLBACK: Set to '1', 'true', or 'yes' to force
            the use of rich fallback instead of fzf. This follows invoke's standard
            config system.

    Examples:
        Select from git branches:
        ```python
        @task
        def checkout(ctx: Context):
            from invoke_toolkit.utils.fzf import select_from_command

            branch = select_from_command(
                ctx,
                "git branch --all",
                prompt="Select branch",
                preview="git log --oneline --color=always {}"
            )
            if branch:
                ctx.run(f"git checkout {branch.strip()}")
        ```

        Select files to delete:
        ```python
        @task
        def cleanup(ctx: Context):
            from invoke_toolkit.utils.fzf import select_from_command

            files = select_from_command(
                ctx,
                "find . -name '*.pyc' -o -name '__pycache__'",
                prompt="Select files to delete",
                multi=True,
                preview="ls -lh {}"
            )
            if files:
                for f in files:
                    ctx.run(f"rm -rf {f}")
        ```

        Select docker container:
        ```python
        @task
        def docker_logs(ctx: Context):
            from invoke_toolkit.utils.fzf import select_from_command

            container = select_from_command(
                ctx,
                "docker ps --format '{{.Names}}'",
                prompt="Select container",
                preview="docker logs --tail 50 {}"
            )
            if container:
                ctx.run(f"docker logs -f {container}")
        ```
    """
    debug(
        f"select_from_command() called: command='{command}', multi={multi}, "
        f"preview={preview is not None}, use_fallback={use_fallback}"
    )

    # Check if force_fallback is enabled in config (includes environment variables)
    # Invoke's config system automatically handles INVOKE_FUZZY_FINDER_FORCE_FALLBACK
    force_fallback = ctx.config.get("fuzzy_finder", {}).get("force_fallback", False)
    debug(f"force_fallback value: {force_fallback}")

    if force_fallback:
        debug(
            "force_fallback enabled (via config or INVOKE_FUZZY_FINDER_FORCE_FALLBACK)"
        )

    fzf_available = is_fzf_available() and not force_fallback

    if not fzf_available:
        if force_fallback:
            debug("force_fallback enabled in config, using rich fallback")
        else:
            debug("fzf not available, attempting fallback")

        if not use_fallback:
            raise RuntimeError(
                "fzf is not installed. Install from: https://github.com/junegunn/fzf"
            )
        # Show warning message (once per session, configurable)
        _show_fzf_warning(ctx, force_fallback=force_fallback)
        # Run command to get choices and use rich fallback
        debug(f"Running command to get choices: {command}")
        result = ctx.run(command, hide=True, warn=True)
        if result is None or not result.ok:
            debug("Command failed to execute")
            return [] if multi else None

        choices = [
            line.strip() for line in result.stdout.strip().split("\n") if line.strip()
        ]
        debug(f"Parsed {len(choices)} choices from command output")
        # Use rich-based fallback with select_1 and exit_0 support
        select_1 = kwargs.get("select_1", False)
        exit_0 = kwargs.get("exit_0", False)
        debug("Using rich fallback selector")
        return _rich_select(choices, prompt, multi, select_1, exit_0)

    # Build fzf command with options
    fzf_cmd = ["fzf"]
    debug("Building fzf command for command output")

    fzf_cmd.append(f'--prompt="{prompt}: "')
    fzf_cmd.append(f"--height={height}")

    if reverse:
        fzf_cmd.append("--reverse")

    if multi:
        fzf_cmd.append("--multi")

    # Handle select-1 option (auto-select if only one match)
    if kwargs.get("select_1"):
        debug("Adding --select-1 flag")
        fzf_cmd.append("--select-1")
        kwargs.pop("select_1")  # Remove from kwargs to avoid duplication

    # Handle exit-0 option (exit immediately if no matches)
    if kwargs.get("exit_0"):
        debug("Adding --exit-0 flag")
        fzf_cmd.append("--exit-0")
        kwargs.pop("exit_0")  # Remove from kwargs to avoid duplication

    if preview:
        fzf_cmd.append(f"--preview='{preview}'")
        fzf_cmd.append(f"--preview-window={preview_window}")

    # Add custom kwargs
    for key, value in kwargs.items():
        flag = key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                fzf_cmd.append(f"--{flag}")
        else:
            # Quote value if it contains spaces
            if isinstance(value, str) and " " in value:
                fzf_cmd.append(f"--{flag}='{value}'")
            else:
                fzf_cmd.append(f"--{flag}={value}")

    debug(f"Running command to get input: {command}")

    # Run command to get output
    cmd_result = ctx.run(command, hide=True, warn=True)
    if cmd_result is None or not cmd_result.ok:
        debug("Command failed to execute")
        return [] if multi else None

    # Run fzf with command output
    return _run_fzf(fzf_cmd, cmd_result.stdout, multi)
