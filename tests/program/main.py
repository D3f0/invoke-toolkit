from invoke_toolkit.testing import TestingToolkitProgram

from invoke_toolkit.collections import ToolkitCollection


ns = ToolkitCollection()
ns.add_collections_from_namespace("program.tasks")
program = TestingToolkitProgram(name="test program", version="0.0.1", namespace=ns)


if __name__ == "__main__":
    program.run()
