"""
A CLI to create CLIs
"""

from .collections import Collection
from .program import InvokeToolkitProgram

ns = Collection()
# TODO: Push down to the program
ns.add_collections_from_namespace("invoke_toolkit.tasks")
program = InvokeToolkitProgram(
    "InvokeToolkit",
    ns,
    name="invtk",
)


if __name__ == "__main__":
    program.run()
