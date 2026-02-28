"""Shell integration tasks for installing shell completions."""

import os
from enum import Enum
from pathlib import Path
from textwrap import dedent

from invoke_toolkit import Context, task


class Shell(str, Enum):
    """Supported shells for completion installation."""

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"


def _detect_shell() -> Shell | None:
    """Detect the current shell from environment or process list."""
    shell_env = os.environ.get("SHELL", "")
    if shell_env:
        shell_name = Path(shell_env).stem
        try:
            return Shell(shell_name)
        except ValueError:
            pass
    return None


def _get_bash_completion_dir() -> Path:
    """Get the bash completion directory, creating ~/.bashrc.d if needed."""
    bashrc_d = Path.home() / ".bashrc.d"
    return bashrc_d


def _get_zsh_completion_dir() -> Path:
    """Get the zsh completion directory."""
    # Use ~/.zfunc as a common location for user completions
    return Path.home() / ".zfunc"


def _get_fish_completion_dir() -> Path:
    """Get the fish completion directory."""
    return Path.home() / ".config" / "fish" / "completions"


def _ensure_bashrc_sources_bashrc_d(ctx: Context) -> bool:
    """
    Ensure ~/.bashrc sources files from ~/.bashrc.d/*.

    Returns True if ~/.bashrc was modified, False otherwise.
    """
    bashrc = Path.home() / ".bashrc"
    bashrc_d = _get_bash_completion_dir()

    source_line = dedent(f"""\
        # Source all files in {bashrc_d}
        if [ -d "{bashrc_d}" ]; then
            for f in "{bashrc_d}"/*.bash; do
                [ -r "$f" ] && source "$f"
            done
            unset f
        fi
        """)

    if not bashrc.exists():
        ctx.console.print(f"[yellow]Creating {bashrc}[/]")
        bashrc.write_text(source_line)
        return True

    bashrc_content = bashrc.read_text()
    if str(bashrc_d) in bashrc_content or ".bashrc.d" in bashrc_content:
        # Already configured
        return False

    ctx.console.print(f"[yellow]Adding bashrc.d sourcing to {bashrc}[/]")
    with open(bashrc, "a", encoding="utf-8") as f:
        f.write("\n" + source_line)
    return True


def _ensure_zshrc_sources_zfunc(ctx: Context) -> bool:
    """
    Ensure ~/.zshrc has fpath configured for completions.

    Returns True if ~/.zshrc was modified, False otherwise.
    """
    zshrc = Path.home() / ".zshrc"
    zfunc = _get_zsh_completion_dir()

    # Lines to add to .zshrc
    setup_lines = dedent(f"""\
        # Add custom completions directory to fpath
        fpath=({zfunc} $fpath)
        # Initialize completion system (if not already done)
        autoload -Uz compinit && compinit
        """)

    if not zshrc.exists():
        ctx.console.print(f"[yellow]Creating {zshrc}[/]")
        zshrc.write_text(setup_lines)
        return True

    zshrc_content = zshrc.read_text()
    if str(zfunc) in zshrc_content or ".zfunc" in zshrc_content:
        # Already configured
        return False

    ctx.console.print(f"[yellow]Adding zfunc to fpath in {zshrc}[/]")
    with open(zshrc, "a", encoding="utf-8") as f:
        f.write("\n" + setup_lines)
    return True


def _install_bash_completion(ctx: Context, binary_name: str = "intk") -> Path:
    """Install bash completion script."""
    completion_dir = _get_bash_completion_dir()
    completion_dir.mkdir(parents=True, exist_ok=True)

    completion_file = completion_dir / f"{binary_name}.bash"

    # Get the completion script from invoke
    result = ctx.run(
        f"{binary_name} --print-completion-script bash", hide=True, warn=True
    )
    if result.failed:
        ctx.rich_exit("[red]Failed to get bash completion script[/]")

    completion_file.write_text(result.stdout)
    ctx.console.print(f"[green]Installed bash completion to {completion_file}[/]")

    # Ensure bashrc sources bashrc.d
    _ensure_bashrc_sources_bashrc_d(ctx)

    return completion_file


def _install_zsh_completion(ctx: Context, binary_name: str = "intk") -> Path:
    """Install zsh completion script."""
    completion_dir = _get_zsh_completion_dir()
    completion_dir.mkdir(parents=True, exist_ok=True)

    # Zsh completion files are named _<command>
    completion_file = completion_dir / f"_{binary_name}"

    # Get the completion script from invoke
    result = ctx.run(
        f"{binary_name} --print-completion-script zsh", hide=True, warn=True
    )
    if result.failed:
        ctx.rich_exit("[red]Failed to get zsh completion script[/]")

    completion_file.write_text(result.stdout)
    ctx.console.print(f"[green]Installed zsh completion to {completion_file}[/]")

    # Ensure zshrc has fpath configured
    _ensure_zshrc_sources_zfunc(ctx)

    return completion_file


def _install_fish_completion(ctx: Context, binary_name: str = "intk") -> Path:
    """Install fish completion script."""
    completion_dir = _get_fish_completion_dir()
    completion_dir.mkdir(parents=True, exist_ok=True)

    completion_file = completion_dir / f"{binary_name}.fish"

    # Get the completion script from invoke
    result = ctx.run(
        f"{binary_name} --print-completion-script fish", hide=True, warn=True
    )
    if result.failed:
        ctx.rich_exit("[red]Failed to get fish completion script[/]")

    completion_file.write_text(result.stdout)
    ctx.console.print(f"[green]Installed fish completion to {completion_file}[/]")

    return completion_file


@task(aliases=["install-completion", "ic"])
def install_completions(
    ctx: Context,
    shell: Shell | None = None,
    binary_name: str = "intk",
) -> None:
    """
    Install shell completions for invoke-toolkit.

    This task installs tab completion for the specified shell:
    - bash: Installs to ~/.bashrc.d/<binary>.bash and configures ~/.bashrc
    - zsh: Installs to ~/.zfunc/_<binary> and configures ~/.zshrc fpath
    - fish: Installs to ~/.config/fish/completions/<binary>.fish

    If no shell is specified, attempts to detect from $SHELL environment variable.

    Examples:
        intk -x install-completions              # Auto-detect shell
        intk -x install-completions --shell bash # Install for bash
        intk -x ic --shell zsh                   # Install for zsh (using alias)
    """
    if shell is None:
        shell = _detect_shell()
        if shell is None:
            ctx.rich_exit(
                "[red]Could not detect shell.[/] "
                "Please specify with [yellow]--shell bash|zsh|fish[/]"
            )
            return  # rich_exit raises Exit, but return for safety in tests
        ctx.console.print(f"[blue]Detected shell:[/] {shell.value}")

    match shell:
        case Shell.BASH:
            _install_bash_completion(ctx, binary_name)
            ctx.console.print(
                "\n[yellow]Please restart your shell or run:[/]\n"
                "  [green]source ~/.bashrc[/]"
            )
        case Shell.ZSH:
            _install_zsh_completion(ctx, binary_name)
            ctx.console.print(
                "\n[yellow]Please restart your shell or run:[/]\n"
                "  [green]source ~/.zshrc[/]"
            )
        case Shell.FISH:
            _install_fish_completion(ctx, binary_name)
            ctx.console.print(
                "\n[yellow]Completions will be available in new fish sessions.[/]"
            )


@task(aliases=["uc"])
def uninstall_completions(
    ctx: Context,
    shell: Shell | None = None,
    binary_name: str = "intk",
) -> None:
    """
    Uninstall shell completions for invoke-toolkit.

    Removes the completion files installed by install-completions.
    Does NOT modify shell configuration files (~/.bashrc, ~/.zshrc).

    Examples:
        intk -x uninstall-completions              # Auto-detect shell
        intk -x uninstall-completions --shell bash # Uninstall for bash
    """
    if shell is None:
        shell = _detect_shell()
        if shell is None:
            ctx.rich_exit(
                "[red]Could not detect shell.[/] "
                "Please specify with [yellow]--shell bash|zsh|fish[/]"
            )
            return  # rich_exit raises Exit, but return for safety in tests
        ctx.console.print(f"[blue]Detected shell:[/] {shell.value}")

    match shell:
        case Shell.BASH:
            completion_file = _get_bash_completion_dir() / f"{binary_name}.bash"
        case Shell.ZSH:
            completion_file = _get_zsh_completion_dir() / f"_{binary_name}"
        case Shell.FISH:
            completion_file = _get_fish_completion_dir() / f"{binary_name}.fish"

    if completion_file.exists():
        completion_file.unlink()
        ctx.console.print(f"[green]Removed {completion_file}[/]")
    else:
        ctx.console.print(f"[yellow]Completion file not found: {completion_file}[/]")


@task
def completion_status(
    ctx: Context,
    binary_name: str = "intk",
) -> None:
    """
    Check the status of shell completion installation.

    Shows whether completions are installed for each supported shell.
    """
    ctx.console.print("[bold]Shell completion status:[/]\n")

    shells_info = [
        (Shell.BASH, _get_bash_completion_dir() / f"{binary_name}.bash"),
        (Shell.ZSH, _get_zsh_completion_dir() / f"_{binary_name}"),
        (Shell.FISH, _get_fish_completion_dir() / f"{binary_name}.fish"),
    ]

    current_shell = _detect_shell()

    for shell, completion_file in shells_info:
        current_marker = " [cyan](current)[/]" if shell == current_shell else ""
        if completion_file.exists():
            status = f"[green]✓ Installed[/] at {completion_file}"
        else:
            status = "[red]✗ Not installed[/]"
        ctx.console.print(f"  {shell.value:5}{current_marker}: {status}")
