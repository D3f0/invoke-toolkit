from invoke.program import Program

from invoke_toolkit.collections import Collection


class TestProgram:
    ...


ns = Collection()
ns.add_collections_from_namespace("program.tasks")
program = Program(name="test program", version="0.0.1", namespace=ns)


if __name__ == "__main__":
    program.run()
