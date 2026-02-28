"""
Tests for invoke_toolkit.extensions.tasks.config module
"""

import json
from pathlib import Path

import pytest
import yaml

from invoke_toolkit import Context
from invoke_toolkit.extensions.tasks.config import (
    ConfigLocation,
    _complete_config_path,
    _find_existing_config_file,
    _get_all_config_paths,
    _get_config_file_paths,
    _get_config_prefix,
    _get_default_config_path,
    _get_expected_type,
    _load_config_file,
    _navigate_config_path,
    _parse_value,
    _save_config_file,
    _set_nested_value,
    _validate_type,
    get,
    set_,
)


@pytest.fixture
def ctx():
    """Returns invoke context"""
    c = Context()
    c.config["run"]["in_stream"] = False
    return c


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create a temporary directory and change to it for config file tests"""
    monkeypatch.chdir(tmp_path)
    return tmp_path


# =============================================================================
# Tests for _parse_value
# =============================================================================


def test_parse_value_string():
    assert _parse_value("hello") == "hello"


def test_parse_value_quoted_string():
    assert _parse_value("'hello world'") == "hello world"


def test_parse_value_integer():
    assert _parse_value("42") == 42


def test_parse_value_float():
    assert _parse_value("3.14") == 3.14


def test_parse_value_boolean_true():
    assert _parse_value("True") is True


def test_parse_value_boolean_false():
    assert _parse_value("False") is False


def test_parse_value_list():
    assert _parse_value("[1, 2, 3]") == [1, 2, 3]


def test_parse_value_list_of_strings():
    assert _parse_value("['a', 'b', 'c']") == ["a", "b", "c"]


def test_parse_value_dict():
    assert _parse_value("{'key': 'value'}") == {"key": "value"}


def test_parse_value_complex_dict():
    result = _parse_value("{'debug': True, 'timeout': 30}")
    assert result == {"debug": True, "timeout": 30}


def test_parse_value_none():
    assert _parse_value("None") is None


def test_parse_value_invalid_returns_string():
    # Invalid Python literals are returned as strings
    assert _parse_value("not-a-literal") == "not-a-literal"


# =============================================================================
# Tests for _navigate_config_path
# =============================================================================


def test_navigate_config_path_simple_key():
    config = {"run": {"echo": True}}
    value, found = _navigate_config_path(config, "run")
    assert found is True
    assert value == {"echo": True}


def test_navigate_config_path_nested_key():
    config = {"run": {"echo": True}}
    value, found = _navigate_config_path(config, "run.echo")
    assert found is True
    assert value is True


def test_navigate_config_path_deeply_nested_key():
    config = {"a": {"b": {"c": {"d": "value"}}}}
    value, found = _navigate_config_path(config, "a.b.c.d")
    assert found is True
    assert value == "value"


def test_navigate_config_path_missing_key():
    config = {"run": {"echo": True}}
    _, found = _navigate_config_path(config, "run.missing")
    assert found is False


def test_navigate_config_path_missing_top_level_key():
    config = {"run": {"echo": True}}
    _, found = _navigate_config_path(config, "missing")
    assert found is False


def test_navigate_config_path_empty_config():
    _, found = _navigate_config_path({}, "any.path")
    assert found is False


# =============================================================================
# Tests for _set_nested_value
# =============================================================================


def test_set_nested_value_simple_key():
    config = {}
    result = _set_nested_value(config, "key", "value")
    assert result == {"key": "value"}


def test_set_nested_value_nested_key():
    config = {}
    result = _set_nested_value(config, "run.echo", True)
    assert result == {"run": {"echo": True}}


def test_set_nested_value_deeply_nested_key():
    config = {}
    result = _set_nested_value(config, "a.b.c.d", "value")
    assert result == {"a": {"b": {"c": {"d": "value"}}}}


def test_set_nested_value_update_existing_value():
    config = {"run": {"echo": False}}
    result = _set_nested_value(config, "run.echo", True)
    assert result == {"run": {"echo": True}}


def test_set_nested_value_add_to_existing_dict():
    config = {"run": {"echo": False}}
    result = _set_nested_value(config, "run.warn", True)
    assert result == {"run": {"echo": False, "warn": True}}


def test_set_nested_value_overwrite_non_dict_with_nested():
    config = {"run": "string_value"}
    result = _set_nested_value(config, "run.echo", True)
    assert result == {"run": {"echo": True}}


# =============================================================================
# Tests for _get_config_prefix
# =============================================================================


def test_get_config_prefix_default(ctx):
    prefix = _get_config_prefix(ctx)
    assert prefix == "invoke"


# =============================================================================
# Tests for _get_config_file_paths
# =============================================================================


def test_get_config_file_paths_local(ctx):
    paths = _get_config_file_paths(ctx, ConfigLocation.LOCAL)
    assert len(paths) == 4
    assert Path("./invoke.yaml") in paths
    assert Path("./invoke.yml") in paths
    assert Path("./invoke.json") in paths
    assert Path("./invoke.py") in paths


def test_get_config_file_paths_user(ctx):
    paths = _get_config_file_paths(ctx, ConfigLocation.USER)
    assert len(paths) == 4
    # Check that paths contain the expected suffixes
    suffixes = {p.suffix for p in paths}
    assert suffixes == {".yaml", ".yml", ".json", ".py"}


def test_get_config_file_paths_system(ctx):
    paths = _get_config_file_paths(ctx, ConfigLocation.SYSTEM)
    assert len(paths) == 4
    assert Path("/etc/invoke.yaml") in paths


# =============================================================================
# Tests for config file persistence (_save_config_file / _load_config_file)
# =============================================================================


def test_save_and_load_yaml(temp_config_dir):
    config_path = temp_config_dir / "test.yaml"
    config_data = {"run": {"echo": True}, "custom": {"ports": [8080, 8443]}}

    _save_config_file(config_path, config_data)
    loaded = _load_config_file(config_path)

    assert loaded == config_data


def test_save_and_load_json(temp_config_dir):
    config_path = temp_config_dir / "test.json"
    config_data = {"run": {"echo": True}, "custom": {"setting": "value"}}

    _save_config_file(config_path, config_data)
    loaded = _load_config_file(config_path)

    assert loaded == config_data


def test_load_nonexistent_file(temp_config_dir):
    config_path = temp_config_dir / "nonexistent.yaml"
    loaded = _load_config_file(config_path)
    assert loaded == {}


def test_save_creates_yaml_format(temp_config_dir):
    config_path = temp_config_dir / "test.yaml"
    config_data = {"key": "value"}

    _save_config_file(config_path, config_data)

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    # Verify it's valid YAML
    parsed = yaml.safe_load(content)
    assert parsed == config_data


def test_save_creates_json_format(temp_config_dir):
    config_path = temp_config_dir / "test.json"
    config_data = {"key": "value"}

    _save_config_file(config_path, config_data)

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    # Verify it's valid JSON
    parsed = json.loads(content)
    assert parsed == config_data


# =============================================================================
# Tests for _find_existing_config_file
# =============================================================================


def test_find_existing_config_file_yaml(ctx, temp_config_dir):
    yaml_path = temp_config_dir / "invoke.yaml"
    yaml_path.write_text("run:\n  echo: true\n")

    found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
    assert found is not None
    assert found.name == "invoke.yaml"


def test_find_existing_config_file_yml(ctx, temp_config_dir):
    yml_path = temp_config_dir / "invoke.yml"
    yml_path.write_text("run:\n  echo: true\n")

    found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
    assert found is not None
    assert found.name == "invoke.yml"


def test_find_existing_config_file_json(ctx, temp_config_dir):
    json_path = temp_config_dir / "invoke.json"
    json_path.write_text('{"run": {"echo": true}}')

    found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
    assert found is not None
    assert found.name == "invoke.json"


def test_find_existing_config_file_returns_none_when_no_config(ctx, temp_config_dir):
    found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
    assert found is None


def test_find_existing_config_file_yaml_takes_precedence_over_yml(ctx, temp_config_dir):
    # Create both yaml and yml files
    yaml_path = temp_config_dir / "invoke.yaml"
    yml_path = temp_config_dir / "invoke.yml"
    yaml_path.write_text("format: yaml\n")
    yml_path.write_text("format: yml\n")

    found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
    assert found is not None
    assert found.name == "invoke.yaml"


# =============================================================================
# Tests for _get_default_config_path
# =============================================================================


def test_get_default_config_path_local(ctx):
    path = _get_default_config_path(ctx, ConfigLocation.LOCAL)
    assert path == Path("./invoke.yaml")


def test_get_default_config_path_system(ctx):
    path = _get_default_config_path(ctx, ConfigLocation.SYSTEM)
    assert path == Path("/etc/invoke.yaml")


# =============================================================================
# Tests for get task
# =============================================================================


def test_get_existing_value(ctx):
    result = get(ctx, "tasks.auto_dash_names")
    assert result is True


def test_get_nested_dict(ctx):
    result = get(ctx, "run")
    assert isinstance(result, dict)
    assert "echo" in result


def test_get_nonexistent_path(ctx):
    result = get(ctx, "nonexistent.path")
    assert result is None


# =============================================================================
# Tests for set_ task
# =============================================================================


def test_set_creates_config_file(ctx, temp_config_dir):
    set_(ctx, "run.echo", "True", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    assert config_path.exists()

    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)

    assert content["run"]["echo"] is True


def test_set_updates_existing_file(ctx, temp_config_dir):
    # Create initial config
    config_path = temp_config_dir / "invoke.yaml"
    config_path.write_text("existing:\n  value: 123\n")

    set_(ctx, "run.echo", "True", ConfigLocation.LOCAL)

    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)

    # Both old and new values should exist
    assert content["existing"]["value"] == 123
    assert content["run"]["echo"] is True


def test_set_with_list_value(ctx, temp_config_dir):
    set_(ctx, "custom.ports", "[8080, 8443]", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)

    assert content["custom"]["ports"] == [8080, 8443]


def test_set_with_dict_value(ctx, temp_config_dir):
    set_(ctx, "custom.settings", "{'debug': True}", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)

    assert content["custom"]["settings"] == {"debug": True}


def test_set_with_json_format(ctx, temp_config_dir):
    set_(ctx, "run.echo", "True", ConfigLocation.LOCAL, format_="json")

    config_path = temp_config_dir / "invoke.json"
    assert config_path.exists()

    with open(config_path, encoding="utf-8") as f:
        content = json.load(f)

    assert content["run"]["echo"] is True


def test_set_uses_existing_file_format(ctx, temp_config_dir):
    # Create initial JSON config
    config_path = temp_config_dir / "invoke.json"
    config_path.write_text('{"existing": "value"}')

    # Set should use the existing JSON file
    set_(ctx, "run.echo", "True", ConfigLocation.LOCAL)

    # JSON file should be updated (not create new YAML)
    with open(config_path, encoding="utf-8") as f:
        content = json.load(f)

    assert content["existing"] == "value"
    assert content["run"]["echo"] is True

    # No YAML file should be created
    yaml_path = temp_config_dir / "invoke.yaml"
    assert not yaml_path.exists()


# =============================================================================
# Tests for _get_all_config_paths
# =============================================================================


def test_get_all_config_paths_simple_dict():
    config = {"key1": "value1", "key2": "value2"}
    paths = _get_all_config_paths(config)
    assert sorted(paths) == ["key1", "key2"]


def test_get_all_config_paths_nested_dict():
    config = {"run": {"echo": True, "warn": False}}
    paths = _get_all_config_paths(config)
    assert sorted(paths) == ["run", "run.echo", "run.warn"]


def test_get_all_config_paths_deeply_nested_dict():
    config = {"a": {"b": {"c": "value"}}}
    paths = _get_all_config_paths(config)
    assert sorted(paths) == ["a", "a.b", "a.b.c"]


def test_get_all_config_paths_mixed_depth():
    config = {
        "simple": "value",
        "nested": {"key": "value"},
        "deep": {"level1": {"level2": "value"}},
    }
    paths = _get_all_config_paths(config)
    expected = [
        "deep",
        "deep.level1",
        "deep.level1.level2",
        "nested",
        "nested.key",
        "simple",
    ]
    assert sorted(paths) == expected


def test_get_all_config_paths_empty_dict():
    paths = _get_all_config_paths({})
    assert not paths


# =============================================================================
# Tests for _complete_config_path
# =============================================================================


def test_complete_config_path_returns_all_paths_for_empty_incomplete(ctx):
    paths = _complete_config_path(ctx, "")
    # Should return many paths from default config
    assert len(paths) > 0
    # Should include known config paths
    assert "run" in paths
    assert "run.echo" in paths


def test_complete_config_path_filters_by_prefix(ctx):
    paths = _complete_config_path(ctx, "run")
    # All paths should start with "run"
    for path in paths:
        assert path.startswith("run")
    # Should include run itself and nested paths
    assert "run" in paths
    assert "run.echo" in paths


def test_complete_config_path_filters_nested_prefix(ctx):
    paths = _complete_config_path(ctx, "run.e")
    # Should match run.echo, run.echo_format, run.echo_stdin, run.env, run.err_stream
    assert len(paths) > 0
    for path in paths:
        assert path.startswith("run.e")


def test_complete_config_path_no_match_returns_empty(ctx):
    paths = _complete_config_path(ctx, "nonexistent_prefix_xyz")
    assert paths == []


def test_complete_config_path_results_are_sorted(ctx):
    paths = _complete_config_path(ctx, "")
    assert paths == sorted(paths)


# =============================================================================
# Tests for completion callbacks attached to tasks
# =============================================================================


def test_get_task_has_completion_callback():
    callbacks = getattr(get, "_completion_callbacks", {})
    assert "path" in callbacks
    assert callable(callbacks["path"])


def test_set_task_has_completion_callback():
    callbacks = getattr(set_, "_completion_callbacks", {})
    assert "path" in callbacks
    assert callable(callbacks["path"])


def test_completion_callback_is_same_function():
    get_callbacks = getattr(get, "_completion_callbacks", {})
    set_callbacks = getattr(set_, "_completion_callbacks", {})
    # Both should use the same completion function
    assert get_callbacks.get("path") is set_callbacks.get("path")


# =============================================================================
# Tests for _get_expected_type
# =============================================================================


def test_get_expected_type_returns_bool_for_bool_value(ctx):
    # run.echo is a bool in default config
    expected = _get_expected_type(ctx, "run.echo")
    assert expected is bool


def test_get_expected_type_returns_str_for_str_value(ctx):
    # run.shell is a str in default config
    expected = _get_expected_type(ctx, "run.shell")
    assert expected is str


def test_get_expected_type_returns_dict_for_dict_value(ctx):
    # run.env is a dict in default config
    expected = _get_expected_type(ctx, "run.env")
    assert expected is dict


def test_get_expected_type_returns_list_for_list_value(ctx):
    # run.watchers is a list in default config
    expected = _get_expected_type(ctx, "run.watchers")
    assert expected is list


def test_get_expected_type_returns_none_for_nonexistent_path(ctx):
    expected = _get_expected_type(ctx, "nonexistent.path")
    assert expected is None


# =============================================================================
# Tests for _validate_type
# =============================================================================


def test_validate_type_valid_bool():
    is_valid, msg = _validate_type(True, bool, "test.path")
    assert is_valid
    assert msg == ""


def test_validate_type_invalid_bool_got_str():
    is_valid, msg = _validate_type("hello", bool, "test.path")
    assert not is_valid
    assert "expected bool" in msg
    assert "got str" in msg


def test_validate_type_valid_str():
    is_valid, _ = _validate_type("hello", str, "test.path")
    assert is_valid


def test_validate_type_invalid_str_got_int():
    is_valid, msg = _validate_type(123, str, "test.path")
    assert not is_valid
    assert "expected str" in msg
    assert "got int" in msg


def test_validate_type_valid_int():
    is_valid, _ = _validate_type(42, int, "test.path")
    assert is_valid


def test_validate_type_valid_float():
    is_valid, _ = _validate_type(3.14, float, "test.path")
    assert is_valid


def test_validate_type_int_allowed_for_float():
    # Numeric promotion: int is allowed where float is expected
    is_valid, _ = _validate_type(42, float, "test.path")
    assert is_valid


def test_validate_type_valid_dict():
    is_valid, _ = _validate_type({"key": "value"}, dict, "test.path")
    assert is_valid


def test_validate_type_invalid_dict_got_list():
    is_valid, msg = _validate_type([1, 2, 3], dict, "test.path")
    assert not is_valid
    assert "expected dict" in msg
    assert "got list" in msg


def test_validate_type_valid_list():
    is_valid, _ = _validate_type([1, 2, 3], list, "test.path")
    assert is_valid


def test_validate_type_invalid_list_got_dict():
    is_valid, msg = _validate_type({"key": "value"}, list, "test.path")
    assert not is_valid
    assert "expected list" in msg
    assert "got dict" in msg


def test_validate_type_none_expected_type_allows_anything():
    # When expected_type is None, any value is valid
    is_valid, _ = _validate_type("anything", None, "test.path")
    assert is_valid

    is_valid, _ = _validate_type(123, None, "test.path")
    assert is_valid

    is_valid, _ = _validate_type([1, 2], None, "test.path")
    assert is_valid


# =============================================================================
# Tests for type validation in set_ task
# =============================================================================


def test_set_rejects_wrong_type_for_bool(ctx, temp_config_dir):
    # run.echo expects bool, should reject str
    set_(ctx, "run.echo", "hello", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    # File should not be created because validation failed
    assert not config_path.exists()


def test_set_accepts_correct_type_for_bool(ctx, temp_config_dir):
    set_(ctx, "run.echo", "True", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    assert config_path.exists()

    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    assert content["run"]["echo"] is True


def test_set_allows_any_type_for_new_path(ctx, temp_config_dir):
    # New paths don't have existing type, so any value is allowed
    set_(ctx, "custom.newkey", "any_value", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    assert config_path.exists()

    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    assert content["custom"]["newkey"] == "any_value"


def test_set_validates_dict_type(ctx, temp_config_dir):
    # run.env expects dict, should reject list
    set_(ctx, "run.env", "[1, 2, 3]", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    assert not config_path.exists()


def test_set_accepts_dict_for_dict_type(ctx, temp_config_dir):
    set_(ctx, "run.env", "{'FOO': 'bar'}", ConfigLocation.LOCAL)

    config_path = temp_config_dir / "invoke.yaml"
    assert config_path.exists()

    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    assert content["run"]["env"] == {"FOO": "bar"}


def test_set_updates_custom_string_value_from_file(ctx, temp_config_dir):
    """
    Regression test for issue where config.set would fail when updating
    a custom string value that exists in invoke.yaml but not in ctx.config.

    This tests the scenario:
    - invoke.yaml has: containerlab.vm_name = "contaierlab"
    - User runs: intk -x config.set containerlab.vm_name 'containerlab'
    - Should succeed and update the value
    """
    config_path = temp_config_dir / "invoke.yaml"
    config_path.write_text("containerlab:\n  vm_name: contaierlab\n")

    # This should succeed despite containerlab.vm_name not being in ctx.config
    set_(ctx, "containerlab.vm_name", "containerlab", ConfigLocation.LOCAL)

    with open(config_path, encoding="utf-8") as f:
        content = yaml.safe_load(f)
    assert content["containerlab"]["vm_name"] == "containerlab"
