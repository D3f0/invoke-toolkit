from typing import List, Optional

from invoke import Context, task
from invoke.exceptions import ParseError

from invoke_toolkit.output import console, rich_exit
from invoke_toolkit.utils.shell import (
    guess_shell,
    path_for_completion_script,
    current_shell,
    CompletionDest,
)
from invoke_toolkit.utils._completions import completions


# TODO: Replace with the contents with code
def get_completion_script(shell: str, names: List[str]) -> str:
    if "/" in shell:
        *_, shell = shell.split("/")
    try:
        script = completions[shell]
    except KeyError:
        err = 'Completion for shell "{}" not supported (options are: {}).'
        raise ParseError(err.format(shell, ", ".join(sorted(completions))))

    # Choose one arbitrary program name for script's own internal invocation
    # (also used to construct completion function names when necessary)
    binary = names[0]

    return script.format(binary=binary, spaced_names=" ".join(names))


@task(autoprint=True)
def print_completion_script(ctx: Context) -> str: ...


@task(default=True)
def install(ctx: Context, shell=None, names=[]):
    """
    Installation of CLI completions
    This is a re-implementation of inv[oke] --print-completion-script
    """
    if not names:
        names = ["invtk"]

    shell = shell or current_shell(ctx) or guess_shell()
    if shell is None:
        rich_exit("Shell couldn't be detected")
    elif "/" in shell:
        *_, shell = shell.split("/")

    console.print(f"[green]{shell}[/green]")
    script = get_completion_script(shell=shell, names=names)

    comp_dest: Optional[CompletionDest] = path_for_completion_script(
        shell=shell, name=names[0]
    )

    if comp_dest is None:
        rich_exit("[bold]Manual interaction required[/bold]", exit_code=2)
    comp_dest.write_text(script)
    console.print(
        "Run \n\n[green]exec $SHELL[/green]\n\nfor the completions to be available"
    )
