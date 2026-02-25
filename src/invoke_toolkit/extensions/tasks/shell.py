"""Shell integration tasks"""

import os
from pathlib import Path
from typing import Annotated

from invoke_toolkit import Context, task

KNOWN_SHELLS = {"bash", "zsh", "fish"}


@task(aliases=["c"])
def completion(
    ctx: Context, shell: Annotated[str | None, "Shell to use"] = None
) -> None:
    """Set up shell completion"""
    if not shell:
        if "SHELL" in os.environ:
            shell = os.getenv("SHELL")
        else:
            # Running commands
            ps_out = ctx.run("ps", hide=True).stdout.splitlines()[1:]
            stems = [line.split()[-1] for line in ps_out]
            for known_shell in KNOWN_SHELLS:
                if known_shell in stems:
                    shell = known_shell

        if shell:
            shell = Path(shell).stem
    match shell:
        case "bash":
            # For bash setup, we don't contaminate the ~/.bashrc file
            # we put these files in a ~/.bashrc.d/ directory and source them
            ctx.run("bash completion setup")
        case "zsh":
            ctx.run("zsh completion setup")
        case "fish":
            ctx.run("fish completion setup")
        case _:
            ctx.rich_exit(f"[red]{shell}[/] not supported")
