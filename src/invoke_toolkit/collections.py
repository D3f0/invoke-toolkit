"""Extended collection with package inspection"""

import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Optional, Union, overload

from invoke.collection import Collection
from invoke.tasks import Task
from invoke.util import debug
from invoke_toolkit.tasks import ToolkitTask
from invoke_toolkit.utils.inspection import get_calling_file_path
from logging import getLogger

logger = getLogger("invoke")


class CollectionError(Exception):
    """Base class for import discovery errors"""


class CollectionNotImportedError(CollectionError): ...


class CollectionCantFindModulePathError(CollectionError): ...


def import_submodules(package_name: str) -> Dict[str, ModuleType]:
    """
    Import all submodules of a module from an imported module
    """
    logger.info("Importing submodules in %s", package_name)
    try:
        package = importlib.import_module(package_name)
    except ImportError as import_error:
        msg = f"Module {package_name} not imported"
        raise CollectionNotImportedError(msg) from import_error
    result = {}
    path = getattr(package, "__path__", None)
    if path is None:
        raise CollectionCantFindModulePathError(package)
    for _loader, name, _is_pkg in pkgutil.walk_packages(package.__path__):
        try:
            result[name] = importlib.import_module(package_name + "." + name)
        except (ImportError, SyntaxError) as error:
            # TODO: Add a flag to show loading exceptions
            logger.exception(error)
            if not name.startswith("__"):
                logger.error(f"Error loading {name} from {package_name}: {error}")

    return result


def clean_collection(collection: "ToolkitCollection") -> None:
    """Removes tasks that are imported from other modules or start with underscores"""

    def user_facing_task(name: str, task: Task) -> bool:
        if name.startswith("_"):
            debug(f"Not adding task {name=} because it starts with _")
            return False
        *_, module_name = task.__module__.split(".")
        # Make sure composed_col is composed-col
        if module_name.replace("_", "-") != collection.name:
            debug(f"Imported task from another place {module_name=} {collection.name=}")
            return False

        return True

    collection.tasks = {
        name: task
        for name, task in collection.tasks.items()
        # if not name.startswith("_")
        if user_facing_task(name, task)
    }


class ToolkitCollection(Collection):
    """
    This Collection allows to load sub-collections from python package paths/namespaces
    like `myscripts.tasks.*`
    """

    @overload
    def __init__(self, **kwargs) -> None: ...

    @overload
    def __init__(
        self,
        name: str,
        *args: Union[Task, ToolkitTask, Collection, "ToolkitCollection"],
        **kwargs,
    ) -> None: ...

    def __init__(
        self, *args: Union[str, Task, ToolkitTask, Collection], **kwargs
    ) -> None:
        debug(f"Instantiating collection with {args=} and {kwargs=}")
        super().__init__(*args, **kwargs)

    def _add_object(self, obj: Any, name: Optional[str] = None) -> None:
        method: Callable
        if isinstance(obj, (Task, ToolkitTask)):
            method = self.add_task
        elif isinstance(obj, (ToolkitCollection, Collection, ModuleType)):
            method = self.add_collection
        else:
            raise TypeError("No idea how to insert {!r}!".format(type(obj)))
        method(obj, name=name)

    def add_collections_from_namespace(self, namespace: str):
        """Iterates over a namespace and imports the submodules"""
        # Attempt simple import
        ok = False
        if namespace not in sys.modules:
            debug(f"Attempting simple import of {namespace}")
            try:
                importlib.import_module(namespace)
                ok = True
            except ImportError:
                logger.warning(f"Failed to import  {namespace}")

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
            coll = ToolkitCollection.from_module(module)
            # TODO: Discover if the namespace has configuration
            #       collection.configure(config)
            self.add_collection(coll=coll, name=name)

    def load_plugins(self):
        """
        This will call to .add_collections_from_namespace but will ensure to
        add the plugin folder to the sys.path
        """

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

    @classmethod
    def from_module(
        cls, module, name=None, config=None, loaded_from=None, auto_dash_names=None
    ) -> "ToolkitCollection":
        return super().from_module(module, name, config, loaded_from, auto_dash_names)

    @classmethod
    def from_package(
        cls, package_path: str, into: "ToolkitCollection"
    ) -> "ToolkitCollection":  # pylint: disable=too-many-branches)
        """
        Creates a collection from a package and configures it
        """
        ns = into or cls()
        global_config: dict[str, str | dict[str, str]] = {}
        for name, module in import_submodules(package_path).items():
            config = getattr(module, "config", None)
            collection: "ToolkitCollection" = ns.from_module(module)
            clean_collection(collection=collection)
            # TODO: Namespaced configuration seems to be an not present when merged!§
            # if config and isinstance(config, (dict, )):
            #     debug(f"🔧 Adding config to module 📦 {name}: {config}")
            #     collection.configure(config)
            if config:
                # FIXME: Detect coitions
                if isinstance(config, (dict,)):
                    debug(f"🔧 Adding config to module 📦 {name}: {config.keys()}")
                    prefixed_config = {name: config}
                    global_config.update(**prefixed_config)
                else:
                    debug(f"In the module {module} the config name is for {config}")
            ns.add_collection(
                collection,
                name=name,
            )

        if global_config:
            debug(f"Adding root collection configuration: {config}")
            ns.configure(global_config)
        return ns
