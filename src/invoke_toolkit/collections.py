import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, Union
from invoke_toolkit.output import console

from invoke.collection import Collection as InvokeCollection
from invoke.util import debug

from invoke_toolkit.utils.inspection import get_calling_file_path


class CollectionError(Exception):
    """Base class for import discovery errors"""


class CollectionNotImportedError(CollectionError): ...


class CollectionCantFindModulePathError(CollectionError): ...


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
    path = getattr(package, "__path__", None)
    if path is None:
        raise CollectionCantFindModulePathError(package)
    discovered = pkgutil.walk_packages(package.__path__)
    debug(f"Discovered packages: {discovered}")
    for _loader, name, _is_pkg in discovered:
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
            # TODO: Discover if the namespace has configuration
            #       collection.configure(config)
            self.add_collection(coll=coll, name=name)

    # XXX: Moved to tasks
    # def load_plugins(self):
    #     """
    #     This will call to .add_collections_from_namespace but will ensure to
    #     add the plugin folder to the sys.path
    #     """

    MULTI_MODULE_BLACK_LIST = {"__init__.py", "tasks.py"}

    @classmethod
    def good_candidate(cls, name: Union[str, Path]) -> bool:
        if isinstance(name, Path):
            name = name.name

        if name in cls.MULTI_MODULE_BLACK_LIST:
            return False
        if name.startswith("_"):
            return False
        if "plugin" in name:
            return False
        if "test" in name:
            return False
        return True

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
            parent_path = str(path.parent)
            if parent_path not in sys.path:
                console.log(f"Adding import path {parent_path} ")
                sys.path.append(parent_path)
            files: Dict[str, Path] = {
                f.name: f for f in path.glob("*.py") if f.is_file()
            }

            spare_files: Dict[str, Path] = {
                name: path for name, path in files.items() if self.good_candidate(path)
            }
            multi_module = len(spare_files) > 0
            if multi_module:
                for file_py in spare_files:
                    module_name = file_py.replace(".py", "")
                    fqmn = f"{path.name}.{module_name}"
                    console.log(f"Importing {fqmn}")
                    module = importlib.import_module(fqmn)
                    col = self.from_module(module)
                    self.add_collection(col)
