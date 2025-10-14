"""
Config object used for invoke attribute resolution
in tasks.
"""

import sys
from invoke.runners import Local
from invoke.util import debug
from rich.syntax import Syntax


class NoStdoutRunner(Local):
    """Invoke runner that prints to stderr when invoke is used with -e/--echo"""

    def echo(self, command):
        if hasattr(self.context, "print"):
            # Safety first
            syn = Syntax(command, "bash")
            self.context.print(syn)
            # output: str = self.opts["echo_format"].format(command=command)
            # self.context.print(output)
        else:
            debug("context is missing print")
            print(self.opts["echo_format"].format(command=command), file=sys.stderr)
