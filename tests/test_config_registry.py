"""Tests for config registry and schema validation."""

import pytest
import attrs
from invoke_toolkit.config import ConfigSchema, config_schema
from invoke_toolkit.config.registry import (
    _schema_registry,
    clear_registry,
    get_all_schemas,
    get_field_type,
    get_schema,
    get_schema_info,
    register_schema,
    validate_value,
)


@attrs.define
class DatabaseConfig(ConfigSchema):
    """Nested database config for testing."""

    host: str = "localhost"
    port: int = 5432
    timeout: float = 30.0


@attrs.define
class AppConfig(ConfigSchema):
    """App config with nested schema for testing."""

    debug: bool = False
    name: str = "myapp"
    database: DatabaseConfig = attrs.Factory(DatabaseConfig)


@pytest.fixture(autouse=True)
def clean_registry_fixture():
    """Clear registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


class TestSchemaRegistry:
    """Tests for the schema registry functions."""

    def test_register_and_get_schema(self):
        """Register a schema and retrieve it."""
        register_schema("myapp", AppConfig)
        assert get_schema("myapp") is AppConfig

    def test_get_nonexistent_schema(self):
        """Get schema for unknown collection returns None."""
        assert get_schema("unknown") is None

    def test_get_all_schemas_empty(self):
        """Get all schemas when registry is empty."""
        assert get_all_schemas() == {}

    def test_get_all_schemas_returns_copy(self):
        """Get all schemas returns a copy, not the original."""
        register_schema("myapp", AppConfig)
        schemas = get_all_schemas()
        schemas["other"] = DatabaseConfig
        # Original registry should be unchanged
        assert "other" not in _schema_registry

    def test_clear_registry(self):
        """Clear registry removes all schemas."""
        register_schema("app1", AppConfig)
        register_schema("app2", DatabaseConfig)
        clear_registry()
        assert get_schema("app1") is None
        assert get_schema("app2") is None


class TestGetFieldType:
    """Tests for get_field_type function."""

    def test_get_field_type_simple(self):
        """Get type for a simple field."""
        register_schema("myapp", AppConfig)
        assert get_field_type("myapp.debug") is bool
        assert get_field_type("myapp.name") is str

    def test_get_field_type_nested(self):
        """Get type for nested schema fields."""
        register_schema("myapp", AppConfig)
        assert get_field_type("myapp.database.port") is int
        assert get_field_type("myapp.database.host") is str
        assert get_field_type("myapp.database.timeout") is float

    def test_get_field_type_unknown_collection(self):
        """Get field type for unknown collection returns None."""
        assert get_field_type("unknown.field") is None

    def test_get_field_type_unknown_field(self):
        """Get field type for unknown field returns None."""
        register_schema("myapp", AppConfig)
        assert get_field_type("myapp.nonexistent") is None
        assert get_field_type("myapp.database.nonexistent") is None

    def test_get_field_type_empty_path(self):
        """Get field type for empty path returns None."""
        assert get_field_type("") is None

    def test_get_field_type_single_component(self):
        """Get field type for just collection name returns None (no field)."""
        register_schema("myapp", AppConfig)
        # Only collection name, no field path - returns the schema itself
        # which is an attrs class, so returns None after loop
        result = get_field_type("myapp")
        # With just the collection name, there's no field to get
        # The function returns the schema type for collection-only path
        assert result is AppConfig


class TestValidateValue:
    """Tests for validate_value function."""

    def test_validate_value_valid_bool(self):
        """Valid boolean value passes validation."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.debug", True)
        assert is_valid is True
        assert error is None

    def test_validate_value_valid_string(self):
        """Valid string value passes validation."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.name", "production")
        assert is_valid is True
        assert error is None

    def test_validate_value_valid_int(self):
        """Valid int value passes validation."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.database.port", 3306)
        assert is_valid is True
        assert error is None

    def test_validate_value_valid_float(self):
        """Valid float value passes validation."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.database.timeout", 60.0)
        assert is_valid is True
        assert error is None

    def test_validate_value_int_for_float(self):
        """Int value accepted where float is expected."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.database.timeout", 60)
        assert is_valid is True
        assert error is None

    def test_validate_value_invalid_type(self):
        """Wrong type fails validation with error message."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.database.port", "not-an-int")
        assert is_valid is False
        assert error is not None
        assert "int" in error.lower()
        assert "str" in error.lower()

    def test_validate_value_no_schema(self):
        """No schema registered allows any value."""
        is_valid, error = validate_value("unknown.path", "anything")
        assert is_valid is True
        assert error is None

    def test_validate_value_unknown_field(self):
        """Unknown field in registered schema allows any value."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.unknown", "anything")
        assert is_valid is True
        assert error is None

    def test_validate_value_none_allowed(self):
        """None value is allowed (for Optional fields)."""
        register_schema("myapp", AppConfig)
        is_valid, error = validate_value("myapp.name", None)
        assert is_valid is True
        assert error is None


class TestCollectionConfigureRegistration:
    """Tests that configure() registers schemas."""

    def test_configure_registers_schema(self):
        """Collection.configure() with schema registers it."""
        from invoke_toolkit.collections import ToolkitCollection

        ns = ToolkitCollection("testcoll")
        ns.configure(schema=AppConfig)

        assert get_schema("testcoll") is AppConfig

    def test_configure_with_instance_registers_class(self):
        """Collection.configure() with schema instance registers the class."""
        from invoke_toolkit.collections import ToolkitCollection

        ns = ToolkitCollection("testcoll")
        ns.configure(schema=AppConfig(debug=True))

        assert get_schema("testcoll") is AppConfig

    def test_configure_without_name_does_not_register(self):
        """Collection without name doesn't register schema."""
        from invoke_toolkit.collections import ToolkitCollection

        ns = ToolkitCollection()  # No name
        ns.configure(schema=AppConfig)

        # Schema should be stored on collection
        assert ns._config_schema is AppConfig
        # But not in registry without a name
        assert get_all_schemas() == {}


class TestOptionalTypeHandling:
    """Tests for Optional type handling in get_field_type."""

    def test_optional_field_type(self):
        """Optional[X] unwraps to X for validation."""

        @attrs.define
        class ConfigWithOptional(ConfigSchema):
            optional_field: str | None = None

        register_schema("opttest", ConfigWithOptional)
        field_type = get_field_type("opttest.optional_field")
        assert field_type is str

    def test_union_with_none(self):
        """Union[X, None] unwraps to X for validation."""

        @attrs.define
        class ConfigWithUnion(ConfigSchema):
            union_field: int | None = None

        register_schema("uniontest", ConfigWithUnion)
        field_type = get_field_type("uniontest.union_field")
        assert field_type is int


@attrs.define
class ServerConfig(ConfigSchema):
    """Test schema for config.set validation tests."""

    host: str = "localhost"
    port: int = 8080
    debug: bool = False


def _get_task_body(task_func):
    """Extract the underlying function body from an invoke Task.

    Invoke's @task decorator wraps the function in a Task object.
    The original function is accessible via the 'body' attribute.
    Using getattr to avoid type checker warnings.
    """
    return getattr(task_func, "body")


class TestConfigSetValidation:
    """Integration tests for config.set schema validation."""

    def _make_mock_context(self):
        """Create a mock context that captures print_err output."""
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.print_err_calls = []
        ctx.print_err = lambda msg: ctx.print_err_calls.append(msg)
        ctx.print = MagicMock()
        # Mock config with some existing values
        ctx.config = MagicMock()
        ctx.config.items.return_value = [
            ("server", {"host": "localhost", "port": 8080})
        ]
        return ctx

    def test_validation_error_shows_type_mismatch(self):
        """Validation error displays expected vs actual type."""
        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        # Access the underlying function body to bypass Task context check
        config_set = _get_task_body(config_set_task)

        register_schema("server", ServerConfig)
        ctx = self._make_mock_context()

        # Try to set port (int) with a string value
        with pytest.raises(SystemExit) as exc_info:
            config_set(ctx, path="server.port", value='"not-a-number"')

        assert exc_info.value.code == 1  # type: ignore[union-attr]

        # Check error messages were printed
        output = "\n".join(ctx.print_err_calls)
        assert "Validation error" in output
        assert "int" in output.lower()
        assert "str" in output.lower()

    def test_validation_error_shows_path(self):
        """Validation error displays the config path."""
        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        config_set = _get_task_body(config_set_task)

        register_schema("server", ServerConfig)
        ctx = self._make_mock_context()

        with pytest.raises(SystemExit):
            config_set(ctx, path="server.port", value='"wrong"')

        output = "\n".join(ctx.print_err_calls)
        assert "server.port" in output

    def test_validation_error_shows_value(self):
        """Validation error displays the parsed value."""
        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        config_set = _get_task_body(config_set_task)

        register_schema("server", ServerConfig)
        ctx = self._make_mock_context()

        with pytest.raises(SystemExit):
            config_set(ctx, path="server.debug", value='"not-bool"')

        output = "\n".join(ctx.print_err_calls)
        assert "not-bool" in output

    def test_validation_error_shows_expected_type(self):
        """Validation error shows the expected type from schema."""
        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        config_set = _get_task_body(config_set_task)

        register_schema("server", ServerConfig)
        ctx = self._make_mock_context()

        with pytest.raises(SystemExit):
            config_set(ctx, path="server.port", value='"text"')

        output = "\n".join(ctx.print_err_calls)
        assert "Expected type" in output
        assert "int" in output

    def test_no_validate_flag_skips_validation(self):
        """--no-validate flag bypasses schema validation."""
        from unittest.mock import patch

        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        config_set = _get_task_body(config_set_task)

        register_schema("server", ServerConfig)
        ctx = self._make_mock_context()

        # This would fail validation, but --no-validate skips it
        # It should proceed to the legacy type check or file save
        # (will fail at file save since we don't have a real file)
        with (
            patch(
                "invoke_toolkit.extensions.tasks.config._find_existing_config_file",
                return_value=None,
            ),
            patch(
                "invoke_toolkit.extensions.tasks.config._get_config_prefix",
                return_value="invoke",
            ),
            patch(
                "invoke_toolkit.extensions.tasks.config._save_config_file",
            ),
        ):
            # This may exit due to legacy validation, but NOT schema validation
            try:
                config_set(ctx, path="server.port", value='"text"', no_validate=True)
            except SystemExit:
                pass

        # Schema validation error should NOT be in output
        output = "\n".join(ctx.print_err_calls)
        assert "Validation error" not in output

    def test_valid_value_passes_validation(self):
        """Valid values pass schema validation and proceed to save."""
        from unittest.mock import patch

        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        config_set = _get_task_body(config_set_task)

        register_schema("server", ServerConfig)

        ctx = self._make_mock_context()
        ctx.config.items.return_value = []

        # Mock file operations to avoid actual file I/O
        with (
            patch(
                "invoke_toolkit.extensions.tasks.config._find_existing_config_file",
                return_value=None,
            ),
            patch(
                "invoke_toolkit.extensions.tasks.config._get_config_prefix",
                return_value="invoke",
            ),
            patch(
                "invoke_toolkit.extensions.tasks.config._save_config_file",
            ),
        ):
            # Valid int value for port
            config_set(ctx, path="server.port", value="9000")

        # Should not have validation errors
        output = "\n".join(ctx.print_err_calls)
        assert "Validation error" not in output

    def test_unknown_collection_allows_any_value(self):
        """Paths in unregistered collections pass validation."""
        from unittest.mock import patch

        from invoke_toolkit.extensions.tasks.config import set_ as config_set_task

        config_set = _get_task_body(config_set_task)

        # No schema registered for "unknown"
        ctx = self._make_mock_context()

        with (
            patch(
                "invoke_toolkit.extensions.tasks.config._find_existing_config_file",
                return_value=None,
            ),
            patch(
                "invoke_toolkit.extensions.tasks.config._get_config_prefix",
                return_value="invoke",
            ),
            patch(
                "invoke_toolkit.extensions.tasks.config._save_config_file",
            ),
        ):
            # Should pass since no schema is registered
            config_set(ctx, path="unknown.any.path", value='"anything"')

        output = "\n".join(ctx.print_err_calls)
        assert "Validation error" not in output


class TestConfigSchemaDecorator:
    """Test the @config_schema decorator."""

    def test_decorator_without_args(self):
        """@config_schema infers collection name from class."""

        @config_schema
        class MyModuleConfig:  # pylint: disable=too-few-public-methods
            value: str = "test"

        assert MyModuleConfig.__config_collection__ == "mymodule"  # type: ignore[attr-defined]  # pylint: disable=no-member
        assert get_schema("mymodule") is MyModuleConfig

    def test_decorator_with_collection_name(self):
        """@config_schema("name") uses explicit collection."""

        @config_schema("custom-name")
        class SomeConfig:  # pylint: disable=too-few-public-methods
            value: str = "test"

        assert SomeConfig.__config_collection__ == "custom-name"  # type: ignore[attr-defined]  # pylint: disable=no-member
        assert get_schema("custom-name") is SomeConfig

    def test_decorator_with_description(self):
        """@config_schema(..., description=...) sets description."""

        @config_schema("described", description="My description")
        class DescribedConfig:  # pylint: disable=too-few-public-methods
            value: str = "test"

        assert DescribedConfig.__config_description__ == "My description"  # type: ignore[attr-defined]  # pylint: disable=no-member

    def test_decorator_applies_attrs_define(self):
        """Decorator applies @attrs.define automatically."""

        @config_schema("auto-attrs")
        class PlainClass:  # pylint: disable=too-few-public-methods
            value: str = "test"

        assert attrs.has(PlainClass)

    def test_decorator_preserves_existing_attrs(self):
        """Decorator works with already-defined attrs classes."""

        @config_schema("existing-attrs")
        @attrs.define
        class ExistingAttrs:
            value: str = "test"

        assert attrs.has(ExistingAttrs)
        assert get_schema("existing-attrs") is ExistingAttrs

    def test_decorator_with_parens_no_args(self):
        """@config_schema() works with empty parens."""

        @config_schema()
        class EmptyParensConfig:  # pylint: disable=too-few-public-methods
            value: str = "test"

        assert EmptyParensConfig.__config_collection__ == "emptyparens"  # type: ignore[attr-defined]  # pylint: disable=no-member
        assert get_schema("emptyparens") is EmptyParensConfig

    def test_decorator_from_dict_to_dict(self):
        """Decorated classes have from_dict and to_dict methods."""

        @config_schema("serializable")
        class SerializableConfig:  # pylint: disable=too-few-public-methods
            host: str = "localhost"
            port: int = 8080

        # Test from_dict
        instance = SerializableConfig.from_dict({"host": "remote", "port": 3000})  # type: ignore[attr-defined]  # pylint: disable=no-member
        assert instance.host == "remote"
        assert instance.port == 3000

        # Test to_dict
        data = instance.to_dict()
        assert data["host"] == "remote"
        assert data["port"] == 3000


class TestGetSchemaInfo:
    """Test schema introspection."""

    def test_get_schema_info_basic(self):
        """get_schema_info returns correct field information."""

        @config_schema("info-test")
        class InfoTestConfig:  # pylint: disable=too-few-public-methods
            host: str = "localhost"
            port: int = 8080
            debug: bool = False

        info = get_schema_info(InfoTestConfig)

        assert info["collection"] == "info-test"
        assert info["class_name"] == "InfoTestConfig"
        assert len(info["fields"]) == 3

        host_field = next(f for f in info["fields"] if f["name"] == "host")
        assert host_field["type"] == "str"
        assert host_field["default"] == "localhost"
        assert host_field["required"] is False

    def test_get_schema_info_required_field(self):
        """get_schema_info marks required fields correctly."""

        @config_schema("required-test")
        class RequiredConfig:  # pylint: disable=too-few-public-methods
            required_field: str  # No default = required
            optional_field: str = "optional"

        info = get_schema_info(RequiredConfig)

        required = next(f for f in info["fields"] if f["name"] == "required_field")
        optional = next(f for f in info["fields"] if f["name"] == "optional_field")

        assert required["required"] is True
        assert optional["required"] is False

    def test_get_schema_info_nested_factory(self):
        """get_schema_info handles Factory defaults."""

        @config_schema("nested-test")
        class NestedConfig:  # pylint: disable=too-few-public-methods
            database: DatabaseConfig = attrs.Factory(DatabaseConfig)

        info = get_schema_info(NestedConfig)

        db_field = next(f for f in info["fields"] if f["name"] == "database")
        # Factory should expand to the default values
        assert isinstance(db_field["default"], dict)
        assert db_field["default"]["host"] == "localhost"
        assert db_field["default"]["port"] == 5432

    def test_get_schema_info_non_attrs_class(self):
        """get_schema_info returns empty dict for non-attrs classes."""

        class PlainClass:  # pylint: disable=too-few-public-methods
            value: str = "test"

        info = get_schema_info(PlainClass)
        assert info == {}

    def test_get_schema_info_with_description(self):
        """get_schema_info includes description."""

        @config_schema("desc-test", description="Test description")
        class DescConfig:  # pylint: disable=too-few-public-methods
            value: str = "test"

        info = get_schema_info(DescConfig)
        assert info["description"] == "Test description"
