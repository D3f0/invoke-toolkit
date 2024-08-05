from typing import List

from invoke import Context, task
from invoke.exceptions import ParseError

from invoke_toolkit.output import console, rich_exit
from invoke_toolkit.utils.shell import guess_shell
from invoke_toolkit.utils._completions import completions


# TODO: Replace with the contents with code
def get_completion_script(shell: str, names: List[str]) -> str:
    try:
        script = completions[shell]
    except KeyError:
        err = 'Completion for shell "{}" not supported (options are: {}).'
        raise ParseError(err.format(shell, ", ".join(sorted(completions))))

    # Choose one arbitrary program name for script's own internal invocation
    # (also used to construct completion function names when necessary)
    binary = names[0]

    return script.format(binary=binary, spaced_names=" ".join(names))


@task(default=True)
def install(ctx: Context, shell=None, names=[]):
    """
    Installation of CLI completions
    This is a re-implementation of inv[oke] --print-completion-script
    """
    if not names:
        names = ["invtk"]

    shell = shell or guess_shell()
    if shell is None:
        rich_exit("Shell couldn't be detected")
    console.print(f"[green]{shell}[/green]")
    console.print(get_completion_script(shell=shell, names=names))
