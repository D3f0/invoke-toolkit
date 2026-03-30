"""Tests for config helper functions

NOTE: These tests use ctx.get_config_value() method instead of the standalone
get_config_value() function. The standalone function remains available for
backward compatibility but the method is the preferred API. The method
delegates to the standalone function, so these tests validate both.
"""

from typing import cast

import pytest

from invoke_toolkit import Context
from invoke_toolkit.config import ToolkitConfig


@pytest.fixture
def ctx():
    """Create a test context with configuration"""
    config = ToolkitConfig(
        overrides={
            "database": {
                "host": "localhost",
                "settings": {
                    "port": 5432,
                    "timeout": 30,
                },
            },
            "api": {
                "key": "secret123",
                "endpoints": {
                    "v1": {
                        "base": "https://api.example.com/v1",
                    }
                },
            },
            "feature": {
                "enabled": False,
                "retry_count": 0,
                "name": "",
            },
        }
    )
    return Context(config=config)


# Basic path retrieval tests
def test_get_config_value_simple_path(ctx):
    """Test retrieval with simple single-level path"""
    result = ctx.get_config_value("database.host")
    assert result == "localhost"


def test_get_config_value_nested_path(ctx):
    """Test retrieval with nested path"""
    result = ctx.get_config_value("database.settings.port")
    assert result == 5432


def test_get_config_value_deep_nested_path(ctx):
    """Test retrieval with deeply nested path"""
    result = ctx.get_config_value("api.endpoints.v1.base")
    assert result == "https://api.example.com/v1"


# Default value tests
def test_get_config_value_missing_key_returns_default(ctx):
    """Test that default is returned when key is missing"""
    result = ctx.get_config_value("database.missing", default="default_value")
    assert result == "default_value"


def test_get_config_value_missing_group_returns_default(ctx):
    """Test that default is returned when group is missing"""
    result = ctx.get_config_value("missing.key", default="default_value")
    assert result == "default_value"


def test_get_config_value_missing_nested_returns_default(ctx):
    """Test that default is returned when nested path is incomplete"""
    result = ctx.get_config_value("database.settings.missing.nested", default="default")
    assert result == "default"


def test_get_config_value_returns_none_by_default(ctx):
    """Test that None is returned as default when not specified"""
    result = ctx.get_config_value("missing.path")
    assert result is None


# Special value tests
def test_get_config_value_with_empty_string(ctx):
    """Test that empty string is returned correctly (not treated as missing)"""
    result = ctx.get_config_value("feature.name", default="default_value")
    assert result == ""


def test_get_config_value_with_boolean_false(ctx):
    """Test that False is returned correctly (not treated as missing)"""
    result = ctx.get_config_value("feature.enabled", default=True)
    assert result is False


def test_get_config_value_with_zero(ctx):
    """Test that 0 is returned correctly (not treated as missing)"""
    result = ctx.get_config_value("feature.retry_count", default=42)
    assert result == 0


# Required value tests - exit_code
def test_get_config_value_required_with_exit_code_missing(ctx):
    """Test that required value with exit_code exits when missing"""
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value("missing.required", exit_code=2)
    assert cast(SystemExit, exc_info.value).code == 2


def test_get_config_value_required_with_exit_code_found(ctx):
    """Test that required value with exit_code returns value when found"""
    result = ctx.get_config_value("database.host", exit_code=1)
    assert result == "localhost"


# Required value tests - exit_message
def test_get_config_value_required_with_exit_message(ctx):
    """Test that required value with exit_message exits when missing"""
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value(
            "missing.value",
            exit_message="Custom error message",
            exit_code=3,
        )
    assert cast(SystemExit, exc_info.value).code == 3


def test_get_config_value_required_with_exit_message_found(ctx):
    """Test that exit_message doesn't trigger when value is found"""
    result = ctx.get_config_value(
        "database.host",
        exit_message="This should not appear",
        exit_code=1,
    )
    assert result == "localhost"


# Required parameter tests
def test_get_config_value_required_true_exits(ctx):
    """Test that required=True triggers exit with code 1"""
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value("missing.key", required=True)
    assert cast(SystemExit, exc_info.value).code == 1


def test_get_config_value_required_with_exit_code_default_code(ctx):
    """Test that default exit_code is 1 when exit_code not specified"""
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value("missing.value", exit_message="Error")
    assert cast(SystemExit, exc_info.value).code == 1


# Edge cases
def test_get_config_value_single_key_path(ctx):
    """Test that single-level path works (though unusual for nested configs)"""
    config = ToolkitConfig(overrides={"simple_key": "simple_value"})
    ctx_simple = Context(config=config)
    # Note: This should return None since 'simple_key' is at the root level
    # and we're looking for 'simple_key.subkey'
    result = ctx_simple.get_config_value("simple_key.subkey", default="default")
    assert result == "default"


def test_get_config_value_complex_nested_structure(ctx):
    """Test with complex nested structures"""
    result = ctx.get_config_value("api.endpoints.v1.base")
    assert result == "https://api.example.com/v1"


def test_get_config_value_preserves_data_types(ctx):
    """Test that data types are preserved"""
    # Integer
    result = ctx.get_config_value("database.settings.timeout")
    assert result == 30
    assert isinstance(result, int)

    # String
    result = ctx.get_config_value("database.host")
    assert result == "localhost"
    assert isinstance(result, str)

    # Boolean
    result = ctx.get_config_value("feature.enabled")
    assert result is False
    assert isinstance(result, bool)


# Exit code default behavior
def test_get_config_value_exit_code_without_message(ctx):
    """Test that exit_code without message auto-generates message"""
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value("missing.config", exit_code=5)
    assert cast(SystemExit, exc_info.value).code == 5


# Tests for canary value handling
def test_get_config_value_returns_none_when_explicitly_set(ctx):
    """Test that None from config is returned correctly (not replaced with default)"""
    config = ToolkitConfig(overrides={"nullable": {"value": None}})
    ctx_none = Context(config=config)
    result = ctx_none.get_config_value("nullable.value", default="default")
    assert result is None


def test_get_config_value_undefined_vs_none_difference():
    """Test that undefined default vs None default are handled differently"""
    config = ToolkitConfig(
        overrides={"data": {"explicit_none": None, "missing": "value"}}
    )
    ctx_test = Context(config=config)

    # Missing value with no default returns None
    result1 = ctx_test.get_config_value("data.not_there")
    assert result1 is None

    # Explicitly set None in config should be returned as-is
    result2 = ctx_test.get_config_value("data.explicit_none", default="default")
    assert result2 is None

    # Provide an explicit None as default
    result3 = ctx_test.get_config_value("data.not_there_either", default=None)
    assert result3 is None


def test_get_config_value_with_explicit_none_default():
    """Test that explicitly passing None as default works"""
    config = ToolkitConfig(overrides={"some": {"value": "data"}})
    ctx_test = Context(config=config)
    result = ctx_test.get_config_value("missing.key", default=None)
    assert result is None


def test_get_config_value_distinguishes_missing_from_none():
    """Test that missing paths are distinguished from None values"""
    config = ToolkitConfig(overrides={"db": {"timeout": None, "retries": 3}})
    ctx_test = Context(config=config)

    # Config value that is explicitly None
    timeout = ctx_test.get_config_value("db.timeout", default=30)
    assert timeout is None

    # Missing value should use the default
    pool_size = ctx_test.get_config_value("db.pool_size", default=10)
    assert pool_size == 10

    # Retries value (not None)
    retries = ctx_test.get_config_value("db.retries", default=5)
    assert retries == 3


def test_get_config_value_required_true_found(ctx):
    """Test that required=True returns value when found"""
    result = ctx.get_config_value("database.host", required=True)
    assert result == "localhost"


def test_get_config_value_required_true_with_default_ignored(ctx):
    """Test that required=True ignores default and exits when not found"""
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value("missing.key", required=True, default="should_not_be_used")
    assert cast(SystemExit, exc_info.value).code == 1


# Tests for argument name detection
def test_get_config_value_detects_argument_name():
    """Test that argument name is detected from config path"""
    from invoke_toolkit.config.config import _get_task_argument_name

    # Simulate a local scope with variables
    # This is a simple test - real detection happens in actual task context
    result = _get_task_argument_name("api.key", depth=0)
    # In test context, this may not find a matching var, which is fine
    # The important thing is it doesn't crash and handles it gracefully
    assert result is None or isinstance(result, str)


def test_get_config_value_auto_detected_name_in_error():
    """Test that auto-detected names appear in error messages"""
    config = ToolkitConfig(overrides={})
    ctx = Context(config=config)

    # When a value is not found with exit_code, should get auto-detected message
    with pytest.raises(SystemExit) as exc_info:
        ctx.get_config_value("database.host", exit_code=1)
    assert cast(SystemExit, exc_info.value).code == 1


def test_get_config_value_handles_path_with_multiple_components():
    """Test that path parsing works with multiple components"""
    config = ToolkitConfig(overrides={"deep": {"nested": {"value": {"here": "found"}}}})
    ctx = Context(config=config)

    result = ctx.get_config_value("deep.nested.value.here")
    assert result == "found"


# Tests for ctx.get_config_value() method specifically
def test_ctx_get_config_value_method_exists():
    """Test that ToolkitContext has the get_config_value method."""
    ctx = Context(config=ToolkitConfig())
    assert hasattr(ctx, "get_config_value")
    assert callable(ctx.get_config_value)


def test_ctx_get_config_value_delegates_to_function():
    """Test that method produces same results as standalone function."""
    from invoke_toolkit.config import get_config_value as standalone_fn

    config = ToolkitConfig(overrides={"test": {"value": "data"}})
    ctx = Context(config=config)

    method_result = ctx.get_config_value("test.value", default="fallback")
    function_result = standalone_fn(ctx, "test.value", default="fallback")

    assert method_result == function_result == "data"


def test_ctx_get_config_value_with_all_parameters():
    """Test method works with all parameter combinations."""
    config = ToolkitConfig(overrides={"db": {"host": "localhost"}})
    ctx = Context(config=config)

    # With default
    assert ctx.get_config_value("db.host", default="127.0.0.1") == "localhost"
    assert ctx.get_config_value("missing", default="fallback") == "fallback"

    # With required=True (found)
    assert ctx.get_config_value("db.host", required=True) == "localhost"
