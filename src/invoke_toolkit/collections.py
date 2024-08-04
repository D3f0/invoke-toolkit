import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, Union

from invoke.collection import Collection as InvokeCollection
from invoke.util import debug

from invoke_toolkit.utils.inspection import get_calling_file_path


class CollectionError(Exception):
    """Base class for import discovery errors"""


class CollectionNotImportedError(CollectionError):
    ...


def import_submodules(package_name: str) -> Dict[str, ModuleType]:
    """
    Import all submodules of a module from an imported module

    :param package_name: Package name
    :type package_name: str
    :rtype: dict[types.ModuleType]
    """
    debug("Importing submodules in %s", package_name)
    try:
        package = sys.modules[package_name]
    except ImportError as import_error:
        msg = f"Module {package_name} not imported"
        raise CollectionNotImportedError(msg) from import_error
    result = {}
    for _loader, name, _is_pkg in pkgutil.walk_packages(package.__path__):
        try:
            result[name] = importlib.import_module(package_name + "." + name)
        except (ImportError, SyntaxError) as error:
            if not name.startswith("__"):
                debug(f"Error loading {name}: {error}")
            else:
                debug(f"Error loading {name}: {error}")

    return result


class Collection(InvokeCollection):
    """
    This Collection allows to load sub-collections from python package paths/namespaces
    like `myscripts.tasks.*`
    """

    def add_collections_from_namespace(self, namespace: str) -> bool:
        """Iterates over a namespace and imports the submodules"""
        # Attempt simple import
        ok = False
        if namespace not in sys.modules:
            debug(f"Attempting simple import of {namespace}")
            try:
                importlib.import_module(namespace)
                ok = True
            except ImportError:
                debug(f"Failed to import  {namespace}")

        if not ok:
            debug("Starting stack inspection to find module")
            # Trying to import relative to caller's script
            caller_path = get_calling_file_path(
                # We're going to get the path of the file where this call
                # was made
                find_call_text=".add_collections_from_namespace("
            )
            debug(f"Adding {caller_path} in order to import {namespace}")
            sys.path.append(caller_path)
            # This should work even if there's no __init__ alongside the
            # program main
            importlib.import_module(namespace)

        for name, module in import_submodules(namespace).items():
            coll = Collection.from_module(module)
            self.add_collection(coll=coll, name=name)

    def load_plugins(self):
        ...

    def load_directory(self, directory: Union[str, Path]) -> None:
        """Loads tasks from a folder"""
        if isinstance(directory, str):
            path = Path(directory)
        elif not isinstance(directory, Path):
            msg = f"The directory to load plugins is not a str/Path: {directory}:{type(directory)}"
            raise TypeError(msg)
        else:
            path = directory

        existing_paths = {pth for pth in sys.path if Path(pth).is_dir()}
        if path not in existing_paths:
            sys.path.append(str(path))
