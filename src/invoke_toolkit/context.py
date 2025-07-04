from invoke.context import Context
from invoke_toolkit.config import InvokeToolkitConfig


class Context(Context):
    config: InvokeToolkitConfig
