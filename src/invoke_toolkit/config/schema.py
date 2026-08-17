"""Attrs-based config schema support with decorators."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar, overload
from collections.abc import Callable

import attrs
import cattrs

T = TypeVar("T", bound="ConfigSchema")

# Converter with common config type hooks
_converter = cattrs.Converter()

# Register Path handling
_converter.register_structure_hook(Path, lambda v, _: Path(v) if v else None)
_converter.register_unstructure_hook(Path, lambda p: str(p) if p else None)


class ConfigSchema:
    """Base class for attrs config schemas.

    Provides structured, type-safe access to configuration data by converting
    between dict representations (used by ToolkitConfig) and attrs classes
    (used for validated, typed access).

    Usage with decorator (preferred):
        @config_schema("mymodule")
        class MyConfig:
            host: str = "localhost"
            port: int = 8080

    Usage with inheritance:
        @attrs.define
        class MyConfig(ConfigSchema):
            host: str = "localhost"
            port: int = 8080

        # Create from dict
        config = MyConfig.from_dict({"host": "prod.db.com"})

        # Convert back to dict
        data = config.to_dict()
    """

    # Set by decorator
    __config_collection__: str | None = None
    __config_description__: str | None = None

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Create instance from dict using cattrs.

        Args:
            data: Dictionary with configuration values. Missing keys use
                  the attrs class defaults.

        Returns:
            Instance of this schema class populated from the dict.

        Raises:
            cattrs.ClassValidationError: If data cannot be structured
                into the schema (e.g., wrong types).
        """
        return _converter.structure(data, cls)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict using cattrs.

        Returns:
            Dictionary representation of this schema instance.
        """
        return _converter.unstructure(self)

    @classmethod
    def get_converter(cls) -> cattrs.Converter:
        """Access the converter for custom hook registration.

        Use this to register custom type hooks for your schema types:

            ConfigSchema.get_converter().register_structure_hook(
                MyCustomType,
                lambda v, _: MyCustomType.parse(v)
            )

        Returns:
            The cattrs Converter instance used by all ConfigSchema classes.
        """
        return _converter


@overload
def config_schema(cls_or_collection: type) -> type: ...


@overload
def config_schema(
    cls_or_collection: str | None = None,
    *,
    description: str | None = None,
) -> Callable[[type], type]: ...


def config_schema(
    cls_or_collection: type | str | None = None,
    *,
    description: str | None = None,
) -> type | Callable[[type], type]:
    """Decorator to define a config schema for a collection.

    Can be used with or without arguments:

        # Simple usage - collection name inferred from class name
        @config_schema
        class MyModuleConfig:
            host: str = "localhost"

        # With explicit collection name
        @config_schema("mymodule")
        class Config:
            host: str = "localhost"

        # With description
        @config_schema("mymodule", description="Database connection settings")
        class DatabaseConfig:
            host: str = "localhost"

    The decorator:
    1. Applies @attrs.define if not already an attrs class
    2. Sets __config_collection__ and __config_description__ attributes
    3. Adds from_dict/to_dict methods for cattrs serialization
    4. Registers the schema in the global registry

    Args:
        cls_or_collection: Either the class (when used as @config_schema)
            or the collection name (when used as @config_schema("name"))
        description: Optional description for the schema

    Returns:
        The decorated class with attrs and ConfigSchema functionality
    """
    # Import here to avoid circular imports - registry imports schema
    from invoke_toolkit.config.registry import register_schema  # pylint: disable=import-outside-toplevel

    def decorator(cls: type) -> type:
        # Determine collection name
        if isinstance(cls_or_collection, str):
            collection_name = cls_or_collection
        else:
            # Infer from class name: MyModuleConfig -> mymodule
            name = cls.__name__
            if name.endswith("Config"):
                name = name[:-6]
            collection_name = name.lower().replace("_", "-")

        # Apply attrs.define if not already an attrs class
        if not attrs.has(cls):
            cls = attrs.define(cls)  # type: ignore[assignment]

        # Add ConfigSchema methods if not already a subclass
        if not issubclass(cls, ConfigSchema):
            cls.from_dict = classmethod(  # type: ignore[attr-defined]
                lambda c, data: _converter.structure(data, c)
            )
            # Lambda is required: binds self as an instance method, then passes to unstructure
            cls.to_dict = lambda self: _converter.unstructure(self)  # type: ignore[attr-defined]  # pylint: disable=unnecessary-lambda
            cls.get_converter = classmethod(lambda c: _converter)  # type: ignore[attr-defined]

        # Set metadata
        cls.__config_collection__ = collection_name  # type: ignore[attr-defined]
        cls.__config_description__ = description or cls.__doc__  # type: ignore[attr-defined]

        # Register in global registry
        register_schema(collection_name, cls)  # type: ignore[arg-type]

        return cls

    # Handle @config_schema vs @config_schema() vs @config_schema("name")
    if cls_or_collection is None:
        # @config_schema() - called with parens but no args
        return decorator
    if isinstance(cls_or_collection, type):
        # @config_schema - called without parens
        return decorator(cls_or_collection)
    # @config_schema("name") - called with collection name
    return decorator
