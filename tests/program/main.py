from invoke.program import Program

from invoke_toolkit.collections import InvokeToolkitCollection
from invoke_toolkit.executor import InvokeToolkitExecutor


class TestProgram: ...


ns = InvokeToolkitCollection()
ns.add_collections_from_namespace("program.tasks")
program = Program(
    name="test program",
    version="0.0.1",
    namespace=ns,
    executor_class=InvokeToolkitExecutor,
)


if __name__ == "__main__":
    program.run()
