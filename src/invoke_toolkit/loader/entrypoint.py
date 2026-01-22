"""Load collections from entrypoints"""

# Example: https://gist.github.com/moreati/44bce66fe0c4febc8d80e064532d4b49
import warnings
from importlib._abc import Loader
from importlib.metadata import entry_points as get_entry_points
from importlib.util import spec_from_loader
from typing import Any

from invoke.loader import FilesystemLoader
from invoke.util import debug

from invoke_toolkit.collections import ToolkitCollection

COLLECTION_ENTRY_POINT = "invoke_toolkit.collection"
PLUGIN_PREFIX = "invoke-toolkit-"


def extract_plugin_short_name(entry_point_name: str) -> str:
    """
    Extract short name from plugin package name.

    If the entry point name follows the pattern 'invoke-toolkit-xxx',
    extract and return 'xxx' as the short name. Otherwise, return the
    original name.

    Args:
        entry_point_name: The entry point name (e.g., 'invoke-toolkit-ext')

    Returns:
        The short name (e.g., 'ext') or the original name if pattern doesn't match
    """
    if entry_point_name.startswith(PLUGIN_PREFIX):
        short_name = entry_point_name[len(PLUGIN_PREFIX) :]
        if short_name:  # Ensure it's not empty after removing prefix
            return short_name
    return entry_point_name


class CollectionLoadError(Exception): ...


class CustomLoader(Loader):
    """
    Usage

    # Create the spec with your custom loader
    attributes = {"ns": Collection, }
    loader = CustomLoader(attributes)
    spec = importlib.util.spec_from_loader("my_module", loader)

    # Create and execute the module
    module = importlib.util.module_from_spec(spec)
    x = spec.loader.exec_module(module)

    """

    def __init__(self, attributes):
        self.attributes = attributes

    def create_module(self, spec):
        return None  # Use default module creation

    def exec_module(self, module):
        """Populate module with your objects"""
        for key, value in self.attributes.items():
            setattr(module, key, value)


class EntryPointLoader(FilesystemLoader):
    """
    Loads Invoke task collections from entry points defined in installed packages.

    Entry points should be defined in package metadata under the 'invoke.collections'
    group. Each entry point should refer to a module or callable that provides
    an Invoke Collection.

    Example in pyproject.toml:
        [project.entry-points."invoke.collections"]
        mypackage = "mypackage.tasks:ns"
        another = "another_package.tasks"
    """

    def find(self, name: str) -> Any:
        """
        Find and load a task collection from entry points.

        Args:
            name: Name of the collection to find

        Returns:
            ModuleSpec with namespace aggregating all matching entry points,
            or falls back to filesystem loader if no entry points found
        """
        entry_points = self._load_entry_points()

        if not entry_points:
            debug(
                f"No entrypoints found {COLLECTION_ENTRY_POINT}. "
                + "Falling back to filesystem loader"
            )
            # Fall back to parent class for filesystem loading
            return super().find(name)

        # Create a namespace that aggregates all entry points
        spec = self._create_compound_module(entry_points)
        if spec is None:
            debug(
                "Could not create compound module from entry points. "
                + "Falling back to filesystem loader"
            )
            # Fall back to parent class for filesystem loading
            return super().find(name)
        return spec

    def _load_entry_points(self):
        """
        Load all entry points from the 'invoke.collections' group.

        Returns:
            Dictionary mapping entry point names to their loaded collections
        """
        entry_points = {}

        # Python 3.10+
        eps = get_entry_points()
        # In Python 3.10+, entry_points() returns EntryPoints with select() method
        group = eps.select(group=COLLECTION_ENTRY_POINT)

        for ep in group:
            try:
                collection = ep.load()
                entry_points[ep.name] = collection
            except Exception as e:
                warnings.warn(
                    f"Failed to load entry point '{ep.name}' from {ep.value}: {e}",
                    RuntimeWarning,
                )

        return entry_points

    def _create_compound_module(self, entry_points) -> Any:
        """
        Create an aggregated namespace from loaded entry points.

        Args:
            entry_points: Dictionary of loaded collections

        Returns:
            ModuleSpec with Invoke Collection with tasks from all entry points,
            or None if no valid entry points were found
        """

        if not entry_points:
            return None

        # Create root collection
        root = ToolkitCollection()
        any_loaded = False
        collection_names_used = {}  # Track which entry points use which collection names

        # Add each loaded collection as a sub-collection
        for name, collection in entry_points.items():
            # Extract short name from plugin packages (e.g., invoke-toolkit-ext -> ext)
            collection_name = extract_plugin_short_name(name)

            # Check for duplicate collection names
            if collection_name in collection_names_used:
                warnings.warn(
                    f"Duplicate collection name '{collection_name}' found. "
                    f"Entry point '{name}' conflicts with '{collection_names_used[collection_name]}'. "
                    f"Only the first one will be loaded.",
                    RuntimeWarning,
                )
                continue

            collection_names_used[collection_name] = name

            if isinstance(collection, ToolkitCollection):
                # It's already a Collection, add it
                root.add_collection(collection, name=collection_name)
                any_loaded = True
            elif hasattr(collection, "__dict__"):
                # It's a module - try to auto-detect ToolkitCollection instances
                toolkit_collections = [
                    obj
                    for attr_name in dir(collection)
                    if not attr_name.startswith("_")
                    for obj in [getattr(collection, attr_name, None)]
                    if isinstance(obj, ToolkitCollection)
                ]

                if toolkit_collections:
                    # Found ToolkitCollection instance(s), use the first one
                    root.add_collection(toolkit_collections[0], name=collection_name)
                    any_loaded = True
                elif hasattr(collection, "tasks"):
                    # It's a module with tasks, wrap it in a Collection
                    root.add_collection(
                        ToolkitCollection.from_module(collection), name=collection_name
                    )
                    any_loaded = True
                else:
                    # Try to treat it as a module
                    try:
                        root.add_collection(
                            ToolkitCollection.from_module(collection),
                            name=collection_name,
                        )
                    except Exception as e:
                        warnings.warn(
                            f"Could not add collection from entry point '{name}': {e}",
                            RuntimeWarning,
                        )
            else:
                # Try to treat it as a module
                try:
                    root.add_collection(
                        ToolkitCollection.from_module(collection), name=collection_name
                    )
                except Exception as e:
                    warnings.warn(
                        f"Could not add collection from entry point '{name}': {e}",
                        RuntimeWarning,
                    )

        # Return None if we didn't manage to load any collections
        if not any_loaded:
            return None

        # Create a module with the collection
        attributes = {
            "ns": root,
        }
        loader = CustomLoader(attributes)
        spec = spec_from_loader("entrypoints", loader)

        return spec
