from invoke_toolkit.program import InvokeToolkitProgram

from invoke_toolkit.collections import Collection


ns = Collection()
ns.add_collections_from_namespace("program.tasks")
program = InvokeToolkitProgram(name="test program", version="0.0.1", namespace=ns)


if __name__ == "__main__":
    program.run()
