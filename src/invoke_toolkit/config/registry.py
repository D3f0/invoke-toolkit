"""Registry for collection config schemas."""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any, Union, get_origin

import attrs

if TYPE_CHECKING:
    from invoke_toolkit.config.schema import ConfigSchema

# Global registry: collection_name -> schema_class
_schema_registry: dict[str, type[ConfigSchema]] = {}


def register_schema(collection_name: str, schema: type[ConfigSchema]) -> None:
    """Register a schema for a collection.

    Args:
        collection_name: The name of the collection (e.g., "mymodule")
        schema: The ConfigSchema subclass to register
    """
    _schema_registry[collection_name] = schema


def get_schema(collection_name: str) -> type[ConfigSchema] | None:
    """Get the registered schema for a collection.

    Args:
        collection_name: The name of the collection

    Returns:
        The schema class, or None if not registered
    """
    return _schema_registry.get(collection_name)


def get_all_schemas() -> dict[str, type[ConfigSchema]]:
    """Get all registered schemas.

    Returns:
        A copy of the schema registry
    """
    return _schema_registry.copy()


def clear_registry() -> None:
    """Clear all registered schemas. Primarily for testing."""
    _schema_registry.clear()


def get_schema_info(schema: type) -> dict[str, Any]:  # pylint: disable=too-many-nested-blocks
    """Get detailed info about a schema for display.

    Returns:
        {
            "collection": "mymodule",
            "class_name": "MyModuleConfig",
            "description": "...",
            "fields": [
                {"name": "host", "type": "str", "default": "localhost", "required": False},
                {"name": "port", "type": "int", "default": 8080, "required": False},
            ]
        }
    """
    if not attrs.has(schema):
        return {}

    fields = []
    for field in attrs.fields(schema):  # pylint: disable=too-many-nested-blocks
        field_info: dict[str, Any] = {
            "name": field.name,
            "type": _format_type(field.type),
            "required": field.default is attrs.NOTHING,
        }

        # Get default value
        if field.default is not attrs.NOTHING:
            if hasattr(field.default, "factory"):
                # attrs.Factory - try to get the default
                factory = field.default
                if getattr(factory, "takes_self", False):
                    field_info["default"] = "<factory(self)>"
                else:
                    try:
                        default_val = factory.factory()
                        # If it's a nested schema, show as dict
                        if attrs.has(type(default_val)):
                            field_info["default"] = attrs.asdict(default_val)
                        else:
                            field_info["default"] = default_val
                    except Exception:  # pylint: disable=broad-exception-caught
                        field_info["default"] = "<factory>"
            else:
                field_info["default"] = field.default
        else:
            field_info["default"] = None

        fields.append(field_info)

    return {
        "collection": getattr(schema, "__config_collection__", None),
        "class_name": schema.__name__,
        "description": getattr(schema, "__config_description__", None)
        or schema.__doc__,
        "fields": fields,
    }


def _format_type(type_hint: Any) -> str:
    """Format a type hint for display."""
    if type_hint is None:
        return "Any"

    # Handle string annotations
    if isinstance(type_hint, str):
        return type_hint

    # Get origin for generic types
    origin = getattr(type_hint, "__origin__", None)
    args = getattr(type_hint, "__args__", ())

    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            args_str = ", ".join(_format_type(a) for a in args)
            return f"{origin_name}[{args_str}]"
        return origin_name

    # Simple type
    return getattr(type_hint, "__name__", str(type_hint))


def get_field_type(path: str) -> type | None:
    """Get the expected type for a config path.

    Navigates through nested ConfigSchema classes to find the type
    annotation for the specified field.

    Args:
        path: Dot-separated path like "mymodule.database.port"

    Returns:
        The type annotation for that field, or None if not found
    """
    parts = path.split(".")
    if not parts:
        return None

    # First part is collection name
    collection_name = parts[0]
    schema = get_schema(collection_name)
    if schema is None:
        return None

    # Navigate through nested schemas
    current_type: type | None = schema
    for part in parts[1:]:
        if current_type is None or not attrs.has(current_type):
            return None

        # Find the field
        fields = attrs.fields(current_type)
        field = None
        for f in fields:
            if f.name == part:
                field = f
                break

        if field is None:
            return None

        current_type = field.type

        # Handle Optional, Union, etc.
        current_type = _unwrap_optional_type(current_type)

    return current_type


def _unwrap_optional_type(type_hint: Any) -> type | None:
    """Unwrap Optional[X] and Union[X, None] to get the inner type.

    Args:
        type_hint: The type annotation (possibly Optional or Union)

    Returns:
        The unwrapped type, or the original if not Optional/Union
    """
    origin = get_origin(type_hint)
    if origin is None:
        return type_hint

    # Handle Union types (including Optional which is Union[X, None])
    if origin in (Union, types.UnionType):
        args = getattr(type_hint, "__args__", ())
        # Filter out NoneType and return the first non-None type
        non_none_args = [a for a in args if a is not type(None)]
        if non_none_args:
            return non_none_args[0]
        return type_hint

    return type_hint


def validate_value(path: str, value: Any) -> tuple[bool, str | None]:
    """Validate a value against the schema for a path.

    Args:
        path: Dot-separated path like "mymodule.database.port"
        value: The value to validate

    Returns:
        Tuple of (is_valid, error_message). If no schema is registered
        for the path's collection, validation passes (permissive mode).
    """
    expected_type = get_field_type(path)
    if expected_type is None:
        # No schema registered or field not found, allow anything
        return True, None

    # Check type compatibility
    if not _is_type_compatible(value, expected_type):
        return (
            False,
            f"Expected {_type_name(expected_type)}, got {type(value).__name__}",
        )

    return True, None


def _is_type_compatible(value: Any, expected_type: type) -> bool:
    """Check if a value is compatible with an expected type.

    Handles common type coercions (e.g., int for float).

    Args:
        value: The value to check
        expected_type: The expected type

    Returns:
        True if the value is compatible with the type
    """
    # Handle None
    if value is None:
        return True

    # Direct instance check
    if isinstance(value, expected_type):
        return True

    # Allow int where float is expected
    if expected_type is float and isinstance(value, int):
        return True

    return False


def _type_name(type_hint: Any) -> str:
    """Get a readable name for a type hint.

    Args:
        type_hint: The type annotation

    Returns:
        A human-readable type name
    """
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__

    origin = getattr(type_hint, "__origin__", None)
    if origin is not None:
        args = getattr(type_hint, "__args__", ())
        arg_names = ", ".join(_type_name(a) for a in args)
        origin_name = getattr(origin, "__name__", str(origin))
        return f"{origin_name}[{arg_names}]"

    return str(type_hint)
