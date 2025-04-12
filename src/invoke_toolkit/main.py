"""
Entry point that creates the program class and executes it
"""

from .collections import InvokeToolkitCollection
from .program import InvokeToolkitProgram

ns = InvokeToolkitCollection()
# TODO: Push down to the program
ns.add_collections_from_namespace("invoke_toolkit.tasks")
program = InvokeToolkitProgram(
    "InvokeToolkit",
    ns,
    name="invtk",
)


if __name__ == "__main__":
    program.run()
