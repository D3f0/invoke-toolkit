import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse
from invoke_toolkit.output import console, rich_exit
from invoke.context import Context
from logging import getLogger


from invoke.collection import Collection
from invoke.util import debug

from invoke_toolkit.utils.inspection import get_calling_file_path

logger = getLogger(__name__)


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
            logger.warning(f"Error loading {name}: {error}")

    return result


class InvokeToolkitCollection(Collection):
    """
    This Collection allows to load sub-collections from python package paths/namespaces
    like `myscripts.tasks.*`
    """

    # FIXME: Add plugin base folder
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

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
            coll = InvokeToolkitCollection.from_module(module)
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
        if name.startswith("_"):
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
                debug(f"Adding import path {parent_path} ")
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
                    debug(f"Importing {fqmn}")
                    module = importlib.import_module(fqmn)
                    col = self.from_module(module)
                    self.add_collection(col)


def add_plugins(
    ctx: Context,
    plugin_dir: Path,
    plugin_ref: str,
    collection: InvokeToolkitCollection,
    force=False,
) -> None:
    """
    Add a repo to the Collections for one-shot runs like CI pipelines.
    """
    context = ctx or Context()

    try:
        parsed = urlparse(plugin_ref)
        if parsed.netloc and parsed.scheme:
            debug(f"Cloning repo {plugin_ref}")
            org, name = parsed.path.strip("/").split("/")[:2]
            name, *_ = name.split(".")
            target_dir = plugin_dir / f"{org}_{name}"

            if target_dir.exists() and not force:
                logger.debug("Plugin already available...")
            else:
                target_dir.mkdir(parents=True)
                console.print(
                    f"Getting plugin from {plugin_ref} ([yellow]git[/yellow])"
                )
                # FIXME: We need to let know we need git here
                context.run(f"git clone {plugin_ref} '{target_dir}'")
        else:
            debug(f"Attenotubg to use {plugin_ref} as a directory...")
            target_dir = Path(parsed.path)
            if not target_dir.is_dir():
                debug("Not a valid folder")
                return

        console.print(f"Loading tasks from '{target_dir}'")
        collection.load_directory(target_dir)

    except Exception as error:
        console.print_exception(show_locals=True)
        rich_exit(f"Can't handle {plugin_ref} yet: {error=}")
