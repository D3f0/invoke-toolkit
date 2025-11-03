from typing import List, Optional
from invoke_toolkit.config.config import ToolkitConfig
from invoke_toolkit.program import ToolkitProgram
from invoke_toolkit.executor import ToolkitExecutor


class NoStdinByDefaultConfig(
    ToolkitConfig, extra_defaults={"run": {"in_stream": False}}
): ...


class TestingToolkitProgram(ToolkitProgram):
    __test__ = False

    def __init__(
        self,
        version=None,
        namespace=None,
        name=None,
        binary=None,
        loader_class=None,
        executor_class=ToolkitExecutor,
        config_class=NoStdinByDefaultConfig,
        binary_names=None,
    ):
        super().__init__(
            version,
            namespace,
            name,
            binary,
            loader_class,
            executor_class,
            config_class,
            binary_names,
        )

    def core_args(self):
        args = super().core_args()

        return args

    def run(self, argv: Optional[List[str]] = None, exit: bool = False) -> None:
        return super().run(argv=argv, exit=exit)
