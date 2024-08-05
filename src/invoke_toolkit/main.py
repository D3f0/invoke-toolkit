"""
A CLI to create CLIs
"""

from invoke.program import Program
from .collections import Collection
from rich.traceback import install


class InvokeToolkitProgram(Program):
    ...


install()
ns = Collection()
ns.add_collections_from_namespace("invoke_toolkit.tasks")
program = Program(
    "InvokeToolkit",
    ns,
    name="invtk",
)
