"""Load collections from entrypoints"""

# Example: https://gist.github.com/moreati/44bce66fe0c4febc8d80e064532d4b49
from importlib._abc import Loader
from importlib.util import module_from_spec, spec_from_loader
from types import ModuleType
from typing import Any

from invoke.loader import FilesystemLoader
from invoke.util import debug

from invoke_toolkit.collections import ToolkitCollection

COLLECTION_ENTRY_POINT = "invoke_toolkit.collection"


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

    def find(self, **kwargs: Any):  # noqa: F821
        """
        Find and load a task collection from entry points.

        Args:
            name: Name of the collection to find
            extra_system_paths: Additional system paths (unused for entry points)

        Returns:
            ModuleSpec with namespace aggregating all matching entry points

        Raises:
            NotFound: If no entry points are found
        """
        entry_points = self._load_entry_points()
        # breakpoint()

        if not entry_points:
            debug(f"No entrypoints found {COLLECTION_ENTRY_POINT}. Using filesystem")

        # Create a namespace that aggregates all entry points
        namespace = self._create_compound_module(entry_points)
        return namespace

    def _load_entry_points(self):
        """
        Load all entry points from the 'invoke.collections' group.

        Returns:
            Dictionary mapping entry point names to their loaded collections
        """
        entry_points = {}

        # Handle both Python 3.10+ (importlib.metadata.entry_points)
        # and older versions (pkg_resources or importlib_metadata)
        try:
            from importlib.metadata import entry_points as get_entry_points

            # Python 3.10+
            eps = get_entry_points()
            if hasattr(eps, "select"):
                # Python 3.10+
                group = eps.select(group=COLLECTION_ENTRY_POINT)
            else:
                # Python 3.9
                group = eps.get(COLLECTION_ENTRY_POINT, [])
        except (ImportError, AttributeError):
            # Fallback to pkg_resources for older Python versions
            try:
                import pkg_resources

                group = pkg_resources.iter_entry_points(COLLECTION_ENTRY_POINT)
            except ImportError:
                return entry_points

        for ep in group:
            try:
                collection = ep.load()
                entry_points[ep.name] = collection
            except Exception as e:
                # Log but continue loading other entry points
                import warnings

                warnings.warn(
                    f"Failed to load entry point '{ep.name}' from {ep.value}: {e}",
                    RuntimeWarning,
                )

        return entry_points

    def _create_compound_module(self, entry_points) -> "ModuleType":
        """
        Create an aggregated namespace from loaded entry points.

        Args:
            entry_points: Dictionary of loaded collections

        Returns:
            Invoke Collection with tasks from all entry points
        """

        if not entry_points:
            return None

        # Create root collection
        root = ToolkitCollection()

        # Add each loaded collection as a sub-collection
        for name, collection in entry_points.items():
            if isinstance(collection, ToolkitCollection):
                # It's already a Collection, add it
                root.add_collection(collection, name=name)
            elif hasattr(collection, "__dict__") and hasattr(collection, "tasks"):
                # It's a module with tasks, wrap it in a Collection
                root.add_collection(
                    ToolkitCollection.from_module(collection), name=name
                )
            else:
                # Try to treat it as a module
                try:
                    root.add_collection(
                        ToolkitCollection.from_module(collection), name=name
                    )
                except Exception as e:
                    import warnings

                    warnings.warn(
                        f"Could not add collection from entry point '{name}': {e}",
                        RuntimeWarning,
                    )

        # return root if root.tasks or root.collections else None
        attributes = {
            "ns": root,
        }
        loader = CustomLoader(attributes)
        spec = spec_from_loader("namespace", loader)

        # Create and execute the module
        module = module_from_spec(spec)
        assert module is not None
        spec.loader.exec_module(module)

        return module
