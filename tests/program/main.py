from invoke_toolkit.program import ToolkitProgram

from invoke_toolkit.collections import ToolkitCollection


ns = ToolkitCollection()
ns.add_collections_from_namespace("program.tasks")
program = ToolkitProgram(name="test program", version="0.0.1", namespace=ns)


if __name__ == "__main__":
    program.run()
