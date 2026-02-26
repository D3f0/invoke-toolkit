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
    _load_config_file,
    _navigate_config_path,
    _parse_value,
    _save_config_file,
    _set_nested_value,
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


class TestParseValue:
    """Tests for _parse_value function"""

    def test_parse_string(self):
        assert _parse_value("hello") == "hello"

    def test_parse_quoted_string(self):
        assert _parse_value("'hello world'") == "hello world"

    def test_parse_integer(self):
        assert _parse_value("42") == 42

    def test_parse_float(self):
        assert _parse_value("3.14") == 3.14

    def test_parse_boolean_true(self):
        assert _parse_value("True") is True

    def test_parse_boolean_false(self):
        assert _parse_value("False") is False

    def test_parse_list(self):
        assert _parse_value("[1, 2, 3]") == [1, 2, 3]

    def test_parse_list_of_strings(self):
        assert _parse_value("['a', 'b', 'c']") == ["a", "b", "c"]

    def test_parse_dict(self):
        assert _parse_value("{'key': 'value'}") == {"key": "value"}

    def test_parse_complex_dict(self):
        result = _parse_value("{'debug': True, 'timeout': 30}")
        assert result == {"debug": True, "timeout": 30}

    def test_parse_none(self):
        assert _parse_value("None") is None

    def test_parse_invalid_returns_string(self):
        # Invalid Python literals are returned as strings
        assert _parse_value("not-a-literal") == "not-a-literal"


class TestNavigateConfigPath:
    """Tests for _navigate_config_path function"""

    def test_simple_key(self):
        config = {"run": {"echo": True}}
        value, found = _navigate_config_path(config, "run")
        assert found is True
        assert value == {"echo": True}

    def test_nested_key(self):
        config = {"run": {"echo": True}}
        value, found = _navigate_config_path(config, "run.echo")
        assert found is True
        assert value is True

    def test_deeply_nested_key(self):
        config = {"a": {"b": {"c": {"d": "value"}}}}
        value, found = _navigate_config_path(config, "a.b.c.d")
        assert found is True
        assert value == "value"

    def test_missing_key(self):
        config = {"run": {"echo": True}}
        _, found = _navigate_config_path(config, "run.missing")
        assert found is False

    def test_missing_top_level_key(self):
        config = {"run": {"echo": True}}
        _, found = _navigate_config_path(config, "missing")
        assert found is False

    def test_empty_config(self):
        _, found = _navigate_config_path({}, "any.path")
        assert found is False


class TestSetNestedValue:
    """Tests for _set_nested_value function"""

    def test_simple_key(self):
        config = {}
        result = _set_nested_value(config, "key", "value")
        assert result == {"key": "value"}

    def test_nested_key(self):
        config = {}
        result = _set_nested_value(config, "run.echo", True)
        assert result == {"run": {"echo": True}}

    def test_deeply_nested_key(self):
        config = {}
        result = _set_nested_value(config, "a.b.c.d", "value")
        assert result == {"a": {"b": {"c": {"d": "value"}}}}

    def test_update_existing_value(self):
        config = {"run": {"echo": False}}
        result = _set_nested_value(config, "run.echo", True)
        assert result == {"run": {"echo": True}}

    def test_add_to_existing_dict(self):
        config = {"run": {"echo": False}}
        result = _set_nested_value(config, "run.warn", True)
        assert result == {"run": {"echo": False, "warn": True}}

    def test_overwrite_non_dict_with_nested(self):
        config = {"run": "string_value"}
        result = _set_nested_value(config, "run.echo", True)
        assert result == {"run": {"echo": True}}


def test_get_config_prefix_default(ctx):
    """Test _get_config_prefix returns 'invoke' by default"""
    prefix = _get_config_prefix(ctx)
    assert prefix == "invoke"


class TestGetConfigFilePaths:
    """Tests for _get_config_file_paths function"""

    def test_local_paths(self, ctx):
        paths = _get_config_file_paths(ctx, ConfigLocation.LOCAL)
        assert len(paths) == 4
        assert Path("./invoke.yaml") in paths
        assert Path("./invoke.yml") in paths
        assert Path("./invoke.json") in paths
        assert Path("./invoke.py") in paths

    def test_user_paths(self, ctx):
        paths = _get_config_file_paths(ctx, ConfigLocation.USER)
        assert len(paths) == 4
        # Check that paths contain the expected suffixes
        suffixes = {p.suffix for p in paths}
        assert suffixes == {".yaml", ".yml", ".json", ".py"}

    def test_system_paths(self, ctx):
        paths = _get_config_file_paths(ctx, ConfigLocation.SYSTEM)
        assert len(paths) == 4
        assert Path("/etc/invoke.yaml") in paths


class TestConfigFilePersistence:
    """Tests for config file loading and saving"""

    def test_save_and_load_yaml(self, temp_config_dir):
        config_path = temp_config_dir / "test.yaml"
        config_data = {"run": {"echo": True}, "custom": {"ports": [8080, 8443]}}

        _save_config_file(config_path, config_data)
        loaded = _load_config_file(config_path)

        assert loaded == config_data

    def test_save_and_load_json(self, temp_config_dir):
        config_path = temp_config_dir / "test.json"
        config_data = {"run": {"echo": True}, "custom": {"setting": "value"}}

        _save_config_file(config_path, config_data)
        loaded = _load_config_file(config_path)

        assert loaded == config_data

    def test_load_nonexistent_file(self, temp_config_dir):
        config_path = temp_config_dir / "nonexistent.yaml"
        loaded = _load_config_file(config_path)
        assert loaded == {}

    def test_save_creates_yaml_format(self, temp_config_dir):
        config_path = temp_config_dir / "test.yaml"
        config_data = {"key": "value"}

        _save_config_file(config_path, config_data)

        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        # Verify it's valid YAML
        parsed = yaml.safe_load(content)
        assert parsed == config_data

    def test_save_creates_json_format(self, temp_config_dir):
        config_path = temp_config_dir / "test.json"
        config_data = {"key": "value"}

        _save_config_file(config_path, config_data)

        with open(config_path, encoding="utf-8") as f:
            content = f.read()

        # Verify it's valid JSON
        parsed = json.loads(content)
        assert parsed == config_data


class TestFindExistingConfigFile:
    """Tests for _find_existing_config_file function"""

    def test_finds_yaml_file(self, ctx, temp_config_dir):
        yaml_path = temp_config_dir / "invoke.yaml"
        yaml_path.write_text("run:\n  echo: true\n")

        found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
        assert found is not None
        assert found.name == "invoke.yaml"

    def test_finds_yml_file(self, ctx, temp_config_dir):
        yml_path = temp_config_dir / "invoke.yml"
        yml_path.write_text("run:\n  echo: true\n")

        found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
        assert found is not None
        assert found.name == "invoke.yml"

    def test_finds_json_file(self, ctx, temp_config_dir):
        json_path = temp_config_dir / "invoke.json"
        json_path.write_text('{"run": {"echo": true}}')

        found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
        assert found is not None
        assert found.name == "invoke.json"

    def test_returns_none_when_no_config(self, ctx, temp_config_dir):
        found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
        assert found is None

    def test_yaml_takes_precedence_over_yml(self, ctx, temp_config_dir):
        # Create both yaml and yml files
        yaml_path = temp_config_dir / "invoke.yaml"
        yml_path = temp_config_dir / "invoke.yml"
        yaml_path.write_text("format: yaml\n")
        yml_path.write_text("format: yml\n")

        found = _find_existing_config_file(ctx, ConfigLocation.LOCAL)
        assert found is not None
        assert found.name == "invoke.yaml"


class TestGetDefaultConfigPath:
    """Tests for _get_default_config_path function"""

    def test_local_default_path(self, ctx):
        path = _get_default_config_path(ctx, ConfigLocation.LOCAL)
        assert path == Path("./invoke.yaml")

    def test_system_default_path(self, ctx):
        path = _get_default_config_path(ctx, ConfigLocation.SYSTEM)
        assert path == Path("/etc/invoke.yaml")


class TestGetTask:
    """Integration tests for the get task"""

    def test_get_existing_value(self, ctx):
        result = get(ctx, "tasks.auto_dash_names")
        assert result is True

    def test_get_nested_dict(self, ctx):
        result = get(ctx, "run")
        assert isinstance(result, dict)
        assert "echo" in result

    def test_get_nonexistent_path(self, ctx, capsys):
        result = get(ctx, "nonexistent.path")
        assert result is None


class TestSetTask:
    """Integration tests for the set task"""

    def test_set_creates_config_file(self, ctx, temp_config_dir):
        set_(ctx, "run.echo", "True", ConfigLocation.LOCAL)

        config_path = temp_config_dir / "invoke.yaml"
        assert config_path.exists()

        with open(config_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content["run"]["echo"] is True

    def test_set_updates_existing_file(self, ctx, temp_config_dir):
        # Create initial config
        config_path = temp_config_dir / "invoke.yaml"
        config_path.write_text("existing:\n  value: 123\n")

        set_(ctx, "run.echo", "True", ConfigLocation.LOCAL)

        with open(config_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Both old and new values should exist
        assert content["existing"]["value"] == 123
        assert content["run"]["echo"] is True

    def test_set_with_list_value(self, ctx, temp_config_dir):
        set_(ctx, "custom.ports", "[8080, 8443]", ConfigLocation.LOCAL)

        config_path = temp_config_dir / "invoke.yaml"
        with open(config_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content["custom"]["ports"] == [8080, 8443]

    def test_set_with_dict_value(self, ctx, temp_config_dir):
        set_(ctx, "custom.settings", "{'debug': True}", ConfigLocation.LOCAL)

        config_path = temp_config_dir / "invoke.yaml"
        with open(config_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        assert content["custom"]["settings"] == {"debug": True}

    def test_set_with_json_format(self, ctx, temp_config_dir):
        set_(ctx, "run.echo", "True", ConfigLocation.LOCAL, format_="json")

        config_path = temp_config_dir / "invoke.json"
        assert config_path.exists()

        with open(config_path, encoding="utf-8") as f:
            content = json.load(f)

        assert content["run"]["echo"] is True

    def test_set_uses_existing_file_format(self, ctx, temp_config_dir):
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


class TestGetAllConfigPaths:
    """Tests for _get_all_config_paths function"""

    def test_simple_dict(self):
        config = {"key1": "value1", "key2": "value2"}
        paths = _get_all_config_paths(config)
        assert sorted(paths) == ["key1", "key2"]

    def test_nested_dict(self):
        config = {"run": {"echo": True, "warn": False}}
        paths = _get_all_config_paths(config)
        assert sorted(paths) == ["run", "run.echo", "run.warn"]

    def test_deeply_nested_dict(self):
        config = {"a": {"b": {"c": "value"}}}
        paths = _get_all_config_paths(config)
        assert sorted(paths) == ["a", "a.b", "a.b.c"]

    def test_mixed_depth(self):
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

    def test_empty_dict(self):
        paths = _get_all_config_paths({})
        assert not paths


class TestCompleteConfigPath:
    """Tests for _complete_config_path function"""

    def test_returns_all_paths_for_empty_incomplete(self, ctx):
        paths = _complete_config_path(ctx, "")
        # Should return many paths from default config
        assert len(paths) > 0
        # Should include known config paths
        assert "run" in paths
        assert "run.echo" in paths

    def test_filters_by_prefix(self, ctx):
        paths = _complete_config_path(ctx, "run")
        # All paths should start with "run"
        for path in paths:
            assert path.startswith("run")
        # Should include run itself and nested paths
        assert "run" in paths
        assert "run.echo" in paths

    def test_filters_nested_prefix(self, ctx):
        paths = _complete_config_path(ctx, "run.e")
        # Should match run.echo, run.echo_format, run.echo_stdin, run.env, run.err_stream
        assert len(paths) > 0
        for path in paths:
            assert path.startswith("run.e")

    def test_no_match_returns_empty(self, ctx):
        paths = _complete_config_path(ctx, "nonexistent_prefix_xyz")
        assert paths == []

    def test_results_are_sorted(self, ctx):
        paths = _complete_config_path(ctx, "")
        assert paths == sorted(paths)


class TestCompletionCallbacksAttached:
    """Tests to verify completion callbacks are properly attached to tasks"""

    def test_get_task_has_completion_callback(self):
        callbacks = getattr(get, "_completion_callbacks", {})
        assert "path" in callbacks
        assert callable(callbacks["path"])

    def test_set_task_has_completion_callback(self):
        callbacks = getattr(set_, "_completion_callbacks", {})
        assert "path" in callbacks
        assert callable(callbacks["path"])

    def test_completion_callback_is_same_function(self):
        get_callbacks = getattr(get, "_completion_callbacks", {})
        set_callbacks = getattr(set_, "_completion_callbacks", {})
        # Both should use the same completion function
        assert get_callbacks.get("path") is set_callbacks.get("path")
