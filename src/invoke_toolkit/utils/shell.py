import os
from pathlib import Path
from typing import Optional, Tuple
from typing_extensions import Annotated
from invoke import Context
from dataclasses import dataclass
from invoke.util import debug


@dataclass
class CompletionDest:
    """Compound type holding where the completion script
    would be written to and if it's an append or create operation"""

    path: Path
    append: bool = True
    create: bool = False

    def __post_init__(self):
        if self.create and self.append:
            # breakpoint()
            raise TypeError("Can't set append and create at the same time.")
        elif not self.create and not self.append:
            raise TypeError("At least one of the append or create flag must be set")
        if isinstance(self.path, str):
            self.path = Path(self.path).expanduser()
        elif not isinstance(self.path, Path):
            raise ValueError(f"{self.path} is not a valid pathlib object.")
        else:
            self.path = self.path.expanduser()

    def write_text(self, text: str):
        if not text:
            return
        if self.append and self.path.exists():
            existing_content = self.path.read_text()
            debug(f"Appedning content to {self.path}")
            self.path.write_text("\n".join(existing_content, text))
        else:
            debug(f"Writing to {self.path}")
            self.path.write_text(text)


def guess_shell() -> Optional[str]:
    shell_path = os.getenv("SHELL", default=None)
    if not shell_path:
        return None
    return Path(shell_path).name


def current_shell(ctx: Context) -> str:
    return ctx.run("echo $0").stdout.strip()


def config_dir(shell: str = "bash", use_folder=True) -> Optional[Path]:
    retval = None
    if not shell:
        return None
    if "/" in shell:
        shell = Path(shell).name
    if shell == "fish":
        retval = "~/.config/fish/"
    elif shell == "bash":
        if use_folder:
            retval = "~/.bashrc.d/"
        else:
            retval = "~"
    elif shell == "zsh":
        if use_folder:
            ...
        else:
            retval = "~"
    return Path(retval).expanduser()


def path_for_completion_script(
    shell: str, name: str
) -> Tuple[Path, Annotated[bool, "Create if True, append if false"]]:
    """
    Resolves the destination where a completion script should be
    written/appended to depending on the shell.

    Basic support for some bash/zsh organization frameworks/techniques:
        - ~/.bashrc.d/ (fund in gitpod)
        - ~/.oh-my-zhs/ (popular ZSH framework, zsh is the default shell in OSX now)
    """

    if shell == "fish":
        completions_dir = Path("~/.config/fish/completions/").expanduser()
        completion_name = f"{name}.fish"
        completion_path = completions_dir / completion_name
        return CompletionDest(completion_path, create=True)
    elif shell == "bash":
        bashrc_d = Path("~/.bashrc.d/").expanduser()
        if not bashrc_d.exists():
            return CompletionDest("~/.bashrc", append=True)
        else:
            # FIXME: We don't know if ~/.bashrc is sourcing
            # the content of ~/.bashrc.d/*
            completion_name = f"{name}.sh"
            completion_path = bashrc_d / completion_name
            return CompletionDest(completion_path, create=True)
    else:
        # https://zsh-manual.netlify.app/completion-system#208-completion-directories
        return CompletionDest(f"~/_comp_{name}", create=True)
