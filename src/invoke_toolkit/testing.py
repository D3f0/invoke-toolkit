from typing import List, Optional
from invoke_toolkit.config.config import ToolkitConfig
from invoke_toolkit.program import ToolkitProgram


class NoStdinByDefaultConfig(
    ToolkitConfig, extra_defaults={"run": {"in_stream": False}}
): ...


class TestingToolkitProgram(ToolkitProgram):
    __test__ = False

    def __init__(self, *args, **kwargs):
        kwargs["config_class"] = NoStdinByDefaultConfig
        super().__init__(*args, **kwargs)

    def core_args(self):
        args = super().core_args()

        return args

    def run(self, argv: Optional[List[str]] = None, exit: bool = False) -> None:
        return super().run(argv=argv, exit=exit)
