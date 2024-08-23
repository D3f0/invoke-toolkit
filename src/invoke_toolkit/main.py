"""
A CLI to create CLIs
"""

from invoke.program import Program
from .program import InvokeToolkitProgram
from .collections import Collection
from rich.traceback import install


ns = Collection()
ns.add_collections_from_namespace("invoke_toolkit.tasks")
program = InvokeToolkitProgram(
    "InvokeToolkit",
    ns,
    name="invtk",
)


if __name__ == "__main__":
    program.run()
