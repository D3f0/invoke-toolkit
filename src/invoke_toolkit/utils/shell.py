import os
from pathlib import Path
from typing import Optional


def guess_shell() -> Optional[str]:
    shell_path = os.getenv("SHELL", default=None)
    if not shell_path:
        return None
    return Path(shell_path).name


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
