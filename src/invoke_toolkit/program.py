"""
A CLI to create CLIs
"""

import os
from typing import List
from invoke.program import Program
from .collections import Collection
from .program import Collection
from rich.traceback import install
from ast import literal_eval


class InvokeToolkitProgram(Program):
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
