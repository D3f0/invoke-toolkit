"""Tests for Collection.configure schema support."""

import pytest
import attrs
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.config import ConfigSchema


@attrs.define
class ServerConfig(ConfigSchema):
    """Server configuration schema for testing."""

    host: str = "localhost"
    port: int = 8080
    debug: bool = False


@attrs.define
class AppConfig(ConfigSchema):
    """App configuration with nested schema for testing."""

    name: str = "myapp"
    server: ServerConfig = attrs.Factory(ServerConfig)


class TestCollectionConfigureSchema:
    """Tests for Collection.configure with attrs schema support."""

    def test_configure_with_schema_class(self):
        """Schema class uses defaults."""
        ns = ToolkitCollection("test")
        ns.configure(schema=ServerConfig)

        config = ns.configuration()
        assert config == {
            "host": "localhost",
            "port": 8080,
            "debug": False,
        }

    def test_configure_with_schema_instance(self):
        """Schema instance uses provided values."""
        ns = ToolkitCollection("test")
        ns.configure(schema=ServerConfig(host="prod.example.com", port=443))

        config = ns.configuration()
        assert config["host"] == "prod.example.com"
        assert config["port"] == 443
        assert config["debug"] is False

    def test_configure_with_nested_schema(self):
        """Nested attrs schemas work."""
        ns = ToolkitCollection("test")
        ns.configure(
            schema=AppConfig(
                name="production", server=ServerConfig(host="prod.db", debug=True)
            )
        )

        config = ns.configuration()
        assert config["name"] == "production"
        assert config["server"]["host"] == "prod.db"
        assert config["server"]["debug"] is True

    def test_configure_schema_with_mapping_override(self):
        """Mapping overrides schema defaults."""
        ns = ToolkitCollection("test")
        ns.configure(schema=ServerConfig, mapping={"port": 9000, "debug": True})

        config = ns.configuration()
        assert config["host"] == "localhost"  # from schema default
        assert config["port"] == 9000  # overridden
        assert config["debug"] is True  # overridden

    def test_configure_nested_mapping_override(self):
        """Nested mapping merges correctly."""
        ns = ToolkitCollection("test")
        ns.configure(schema=AppConfig, mapping={"server": {"port": 443}})

        config = ns.configuration()
        assert config["name"] == "myapp"  # schema default
        assert config["server"]["host"] == "localhost"  # nested default
        assert config["server"]["port"] == 443  # overridden

    def test_configure_invalid_schema_type(self):
        """Invalid schema raises TypeError."""
        ns = ToolkitCollection("test")
        with pytest.raises(TypeError, match="ConfigSchema"):
            ns.configure(schema={"not": "a schema"})  # type: ignore[arg-type]

    def test_configure_stores_schema_class(self):
        """Schema class is stored for later validation."""
        ns = ToolkitCollection("test")
        ns.configure(schema=ServerConfig)

        assert ns._config_schema is ServerConfig

    def test_configure_stores_schema_class_from_instance(self):
        """Schema class is extracted and stored from instance."""
        ns = ToolkitCollection("test")
        ns.configure(schema=ServerConfig(port=9000))

        assert ns._config_schema is ServerConfig

    def test_traditional_configure_still_works(self):
        """Original dict-only configure still works."""
        ns = ToolkitCollection("test")
        ns.configure({"key": "value", "nested": {"inner": 123}})

        config = ns.configuration()
        assert config["key"] == "value"
        assert config["nested"]["inner"] == 123

    def test_configure_with_none_mapping_and_schema(self):
        """None mapping with schema works."""
        ns = ToolkitCollection("test")
        ns.configure(mapping=None, schema=ServerConfig)

        config = ns.configuration()
        assert config["host"] == "localhost"
        assert config["port"] == 8080

    def test_configure_with_empty_mapping_and_schema(self):
        """Empty mapping with schema uses schema defaults."""
        ns = ToolkitCollection("test")
        ns.configure(mapping={}, schema=ServerConfig)

        config = ns.configuration()
        assert config["host"] == "localhost"
        assert config["port"] == 8080

    def test_configure_only_mapping_no_schema(self):
        """Traditional configure with only mapping works."""
        ns = ToolkitCollection("test")
        ns.configure(mapping={"custom": "value"})

        config = ns.configuration()
        assert config["custom"] == "value"

    def test_deep_merge_nested_dicts(self):
        """Deep merge correctly handles nested dictionaries."""
        ns = ToolkitCollection("test")
        ns.configure(
            schema=AppConfig(name="app1"),
            mapping={"server": {"host": "custom.host", "extra": "data"}},
        )

        config = ns.configuration()
        assert config["name"] == "app1"  # from schema instance
        assert config["server"]["host"] == "custom.host"  # overridden
        assert config["server"]["port"] == 8080  # from nested schema default
        assert config["server"]["extra"] == "data"  # new key from mapping

    def test_schema_class_without_instance_not_set_initially(self):
        """Initially _config_schema is None."""
        ns = ToolkitCollection("test")
        assert ns._config_schema is None
