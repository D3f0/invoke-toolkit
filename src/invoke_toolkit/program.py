"""
A CLI to create CLIs
"""

import os
from ast import literal_eval
from pathlib import Path
from typing import List, Optional

from invoke.program import Program
from rich.traceback import install
from invoke_toolkit.collections import InvokeCollection
from appdirs import user_data_dir


class InvokeToolkitProgram(Program):
    collection: InvokeCollection
    author: str = "InvokeToolkitTeam"

    def run(self, argv: List[str] | None = None, exit: bool = True) -> None:
        """
        Runs the program using invoke code but pre-enabling rich traceback.
        """
        env_disable_rich_tb = os.getenv("NO_RICH_TB", "0")
        try:
            enable = not literal_eval(env_disable_rich_tb)
        except Exception:
            enable = True
        if enable:
            install()

        return super().run(argv, exit)

    def create_config(self) -> None:
        """Adds the invoke-toolkit extra keys"""
        super().create_config()
        section = self.config.setdefault("invoke-toolkit", {})
        section["instance"] = self

    @property
    def plugin_dir(self):
        location = user_data_dir(type(self).__name__, self.author)
        path = Path(location) / "plugins"

        if not path.exists():
            path.mkdir(parents=True)
        return path
