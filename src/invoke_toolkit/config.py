from invoke.config import Config
from typing import Dict, Any
from .runner import InvokeToolkitRunner


class InvokeToolkitConfig(Config):
    @staticmethod
    def global_defaults() -> Dict[str, Any]:
        """
        Return the core default settings for Invoke Toolkit.

        Look at the definition of the supper class
        """

        global_defaults = Config.global_defaults()
        # Change the default runner
        global_defaults["runners"]["local"] = InvokeToolkitRunner
        return global_defaults
