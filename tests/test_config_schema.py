"""Tests for attrs-based config schemas."""

import pytest
import attrs
from invoke_toolkit.config.schema import ConfigSchema
from invoke_toolkit.config import ToolkitConfig


@attrs.define
class DatabaseConfig(ConfigSchema):
    """Nested config for database settings."""

    host: str = "localhost"
    port: int = 5432
    pool_size: int = 5


@attrs.define
class AppConfig(ConfigSchema):
    """Top-level app config with nested database config."""

    debug: bool = False
    timeout: float = 30.0
    database: DatabaseConfig = attrs.Factory(DatabaseConfig)


class TestConfigSchema:
    """Test ConfigSchema base functionality."""

    def test_from_dict_simple(self):
        """Test creating schema from flat dict."""
        data = {"host": "prod.db.com", "port": 3306, "pool_size": 10}
        config = DatabaseConfig.from_dict(data)

        assert config.host == "prod.db.com"
        assert config.port == 3306
        assert config.pool_size == 10

    def test_from_dict_with_defaults(self):
        """Test that missing keys use defaults."""
        data = {"host": "prod.db.com"}
        config = DatabaseConfig.from_dict(data)

        assert config.host == "prod.db.com"
        assert config.port == 5432  # default
        assert config.pool_size == 5  # default

    def test_from_dict_nested(self):
        """Test creating schema with nested attrs class."""
        data = {
            "debug": True,
            "timeout": 60.0,
            "database": {"host": "prod.db.com", "port": 3306},
        }
        config = AppConfig.from_dict(data)

        assert config.debug is True
        assert config.timeout == 60.0
        assert config.database.host == "prod.db.com"
        assert config.database.port == 3306
        assert config.database.pool_size == 5  # nested default

    def test_to_dict_simple(self):
        """Test converting schema to dict."""
        config = DatabaseConfig(host="test.db", port=1234, pool_size=20)
        data = config.to_dict()

        assert data == {"host": "test.db", "port": 1234, "pool_size": 20}

    def test_to_dict_nested(self):
        """Test converting nested schema to dict."""
        config = AppConfig(debug=True, database=DatabaseConfig(host="nested.db"))
        data = config.to_dict()

        assert data["debug"] is True
        assert data["database"]["host"] == "nested.db"

    def test_roundtrip(self):
        """Test from_dict -> modify -> to_dict roundtrip."""
        original = {"debug": False, "timeout": 30.0, "database": {"host": "a"}}
        config = AppConfig.from_dict(original)
        config.debug = True
        config.database.host = "b"
        result = config.to_dict()

        assert result["debug"] is True
        assert result["database"]["host"] == "b"


class TestToolkitConfigIntegration:
    """Test integration with ToolkitConfig."""

    def test_as_schema(self):
        """Test converting config section to attrs schema."""
        config = ToolkitConfig(
            overrides={"database": {"host": "test.db", "port": 3306}}
        )

        db = config.as_schema(DatabaseConfig, "database")

        assert isinstance(db, DatabaseConfig)
        assert db.host == "test.db"
        assert db.port == 3306
        assert db.pool_size == 5  # from schema default

    def test_update_from(self):
        """Test updating config from attrs schema."""
        config = ToolkitConfig(overrides={"database": {"host": "old.db", "port": 5432}})

        # Get as schema, modify, update back
        db = config.as_schema(DatabaseConfig, "database")
        db.host = "new.db"
        db.port = 3307
        config.update_from(db, "database")

        assert config.database.host == "new.db"
        assert config.database.port == 3307

    def test_as_schema_type_error(self):
        """Test that non-ConfigSchema raises TypeError."""
        config = ToolkitConfig(overrides={"x": 1})

        with pytest.raises(TypeError, match="ConfigSchema subclass"):
            config.as_schema(dict)

    def test_nested_config_roundtrip(self):
        """Test full roundtrip with nested config."""
        config = ToolkitConfig(
            overrides={
                "app": {
                    "debug": False,
                    "timeout": 30.0,
                    "database": {"host": "localhost"},
                }
            }
        )

        # Convert to schema
        app = config.as_schema(AppConfig, "app")
        assert app.debug is False
        assert app.database.host == "localhost"

        # Modify
        app.debug = True
        app.database.host = "production.db"

        # Update back
        config.update_from(app, "app")

        # Verify
        assert config.app.debug is True
        assert config.app.database.host == "production.db"
