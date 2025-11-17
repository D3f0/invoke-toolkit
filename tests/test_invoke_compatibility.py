# pyright: reportAny=false


import inspect
from types import ModuleType
from typing import Any

import invoke

# We import it from invoke in case our top-level Result is somehow broken

import invoke_toolkit


def test_invoke_top_level_imports():
    def get_module_members(mod: ModuleType) -> dict[str, Any]:
        res = {}
        for name in dir(mod):
            if name.startswith("_"):
                continue
            obj = getattr(mod, name)
            if hasattr(obj, "__module__") and obj.__module__ == "typing":
                continue
            if isinstance(obj, ModuleType):
                continue
            res[name] = obj
        return res

    invoke_toplevel_symbols = get_module_members(invoke)
    toolkit_toplevel_symbols = get_module_members(invoke_toolkit)

    for name, obj in invoke_toplevel_symbols.items():
        assert name in toolkit_toplevel_symbols
        toolkit_obj = toolkit_toplevel_symbols[name]
        if inspect.isclass(obj):
            assert inspect.isclass(toolkit_obj) and issubclass(toolkit_obj, obj)
        else:
            assert type(obj) is type(toolkit_obj)
