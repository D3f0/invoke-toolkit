"""Original invoke config tests adapted for ToolkitConfig.

These tests are adapted from the invoke project's tests/config.py file
to verify ToolkitConfig maintains compatibility with invoke's Config behavior.

Source: https://github.com/pyinvoke/invoke/blob/main/tests/config.py
"""

# pylint: disable=no-member,unsupported-delete-operation

import os
import pickle
from os.path import join
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from invoke import config as config_mod  # for accessing mocks
from invoke.config import Config
from invoke.exceptions import (
    AmbiguousEnvVar,
    UncastableEnvVar,
    UnknownFileType,
    UnpicklableConfigMember,
)
from invoke.runners import Local
from invoke.terminals import WINDOWS

# Use absolute path based on __file__ for CI compatibility
# (relative imports fail when pytest runs from different directories)
support = Path(__file__).parent / "_support"


def skip_if_windows(fn):
    """Decorator to skip tests on Windows platforms."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if WINDOWS:
            pytest.skip()
        return fn(*args, **kwargs)

    return wrapper


# Apply integration fixture to all tests in this module
pytestmark = pytest.mark.usefixtures("integration")


CONFIGS_PATH = "configs"
TYPES = ("yaml", "yml", "json", "python")


def _load(kwarg, type_, **kwargs):
    """Helper to load configs from the configs/ directory."""
    path = join(CONFIGS_PATH, type_ + "/")
    kwargs[kwarg] = path
    return Config(**kwargs)


class TestConfigClassAttrs:
    """Test class attribute configuration."""

    class TestPrefix:
        def test_defaults_to_invoke(self):
            assert Config().prefix == "invoke"

        @patch.object(Config, "_load_yaml")
        def test_informs_config_filenames(self, load_yaml):
            class MyConf(Config):
                prefix = "other"

            MyConf(system_prefix="dir/")
            load_yaml.assert_any_call("dir/other.yaml")

        def test_informs_env_var_prefix(self):
            os.environ["OTHER_FOO"] = "bar"

            class MyConf(Config):
                prefix = "other"

            c = MyConf(defaults={"foo": "notbar"})
            c.load_shell_env()
            assert c.foo == "bar"

    class TestFilePrefix:
        def test_defaults_to_None(self):
            assert Config().file_prefix is None

        @patch.object(Config, "_load_yaml")
        def test_informs_config_filenames(self, load_yaml):
            class MyConf(Config):
                file_prefix = "other"

            MyConf(system_prefix="dir/")
            load_yaml.assert_any_call("dir/other.yaml")

    class TestEnvPrefix:
        def test_defaults_to_None(self):
            assert Config().env_prefix is None

        def test_informs_env_vars_loaded(self):
            os.environ["OTHER_FOO"] = "bar"

            class MyConf(Config):
                env_prefix = "other"

            c = MyConf(defaults={"foo": "notbar"})
            c.load_shell_env()
            assert c.foo == "bar"


class TestGlobalDefaults:
    """Test global_defaults static method."""

    @skip_if_windows
    def test_basic_settings(self):
        """Test that global defaults contain expected keys and structure.

        Note: The 'shell' value varies by platform (e.g., 'bash' vs '/bin/bash'),
        so we compare structure without the exact shell path.
        """
        defaults = Config.global_defaults()

        # Verify top-level structure
        assert set(defaults.keys()) == {"run", "runners", "sudo", "tasks", "timeouts"}

        # Verify run config (excluding platform-dependent 'shell')
        run_config = defaults["run"]
        assert run_config["asynchronous"] is False
        assert run_config["disown"] is False
        assert run_config["dry"] is False
        assert run_config["echo"] is False
        assert run_config["echo_format"] == "\033[1;37m{command}\033[0m"
        assert run_config["echo_stdin"] is None
        assert run_config["encoding"] is None
        assert run_config["env"] == {}
        assert run_config["err_stream"] is None
        assert run_config["fallback"] is True
        assert run_config["hide"] is None
        assert run_config["in_stream"] is None
        assert run_config["out_stream"] is None
        assert run_config["pty"] is False
        assert run_config["replace_env"] is False
        # Shell path varies by platform - just verify it contains 'bash'
        assert "bash" in run_config["shell"]
        assert run_config["warn"] is False
        assert run_config["watchers"] == []

        # Verify other sections
        assert defaults["runners"] == {"local": Local}
        assert defaults["sudo"] == {
            "password": None,
            "prompt": "[sudo] password: ",
            "user": None,
        }
        assert defaults["tasks"] == {
            "auto_dash_names": True,
            "collection_name": "tasks",
            "dedupe": True,
            "executor_class": None,
            "ignore_unknown_help": False,
            "search_root": None,
        }
        assert defaults["timeouts"] == {"command": None}


class TestInit:
    """Test __init__ behavior."""

    def test_can_be_empty(self):
        assert Config().__class__ == Config

    @patch.object(Config, "_load_yaml")
    def test_configure_global_location_prefix(self, load_yaml):
        Config(system_prefix="meh/")
        load_yaml.assert_any_call("meh/invoke.yaml")

    @skip_if_windows
    @patch.object(Config, "_load_yaml")
    def test_default_system_prefix_is_etc(self, load_yaml):
        Config()
        load_yaml.assert_any_call("/etc/invoke.yaml")

    @patch.object(Config, "_load_yaml")
    def test_configure_user_location_prefix(self, load_yaml):
        Config(user_prefix="whatever/")
        load_yaml.assert_any_call("whatever/invoke.yaml")

    @patch.object(Config, "_load_yaml")
    def test_default_user_prefix_is_homedir_plus_dot(self, load_yaml):
        Config()
        config_mod.expanduser.assert_any_call("~/.invoke.yaml")
        load_yaml.assert_any_call(config_mod.expanduser("~/.invoke.yaml"))

    @patch.object(Config, "_load_yaml")
    def test_configure_project_location(self, load_yaml):
        Config(project_location="someproject").load_project()
        load_yaml.assert_any_call(join("someproject", "invoke.yaml"))

    @patch.object(Config, "_load_yaml")
    def test_configure_runtime_path(self, load_yaml):
        Config(runtime_path="some/path.yaml").load_runtime()
        load_yaml.assert_any_call("some/path.yaml")

    def test_accepts_defaults_dict_kwarg(self):
        c = Config(defaults={"super": "low level"})
        assert c.super == "low level"

    def test_overrides_dict_is_first_posarg(self):
        c = Config({"new": "data", "run": {"hide": True}})
        assert c.run.hide is True
        assert c.run.warn is False
        assert c.new == "data"

    def test_overrides_dict_is_also_a_kwarg(self):
        c = Config(overrides={"run": {"hide": True}})
        assert c.run.hide is True

    @patch.object(Config, "load_system")
    @patch.object(Config, "load_user")
    @patch.object(Config, "merge")
    def test_system_and_user_files_loaded_automatically(self, merge, load_u, load_s):
        Config()
        load_s.assert_called_once_with(merge=False)
        load_u.assert_called_once_with(merge=False)
        merge.assert_called_once_with()

    @patch.object(Config, "load_system")
    @patch.object(Config, "load_user")
    def test_can_defer_loading_system_and_user_files(self, load_u, load_s):
        config = Config(lazy=True)
        assert not load_s.called
        assert not load_u.called
        assert config.run.echo is False


class TestBasicAPI:
    """Test basic API components."""

    def test_can_be_used_directly_after_init(self):
        c = Config({"lots of these": "tests look similar"})
        assert c["lots of these"] == "tests look similar"

    def test_allows_dict_and_attr_access(self):
        c = Config({"foo": "bar"})
        assert c.foo == "bar"
        assert c["foo"] == "bar"

    def test_nested_dict_values_also_allow_dual_access(self):
        c = Config({"foo": "bar", "biz": {"baz": "boz"}})
        assert c.foo == "bar"
        assert c["foo"] == "bar"
        assert c.biz.baz == "boz"
        assert c["biz"]["baz"] == "boz"
        assert c.biz["baz"] == "boz"
        assert c["biz"].baz == "boz"

    def test_attr_access_has_useful_error_msg(self):
        c = Config()
        try:
            c.nope
        except AttributeError as e:
            # Just check it's a useful message with key info
            assert "nope" in str(e)
            assert "Valid keys" in str(e)
        else:
            assert False, "Didn't get an AttributeError on bad key!"

    def test_subkeys_get_merged_not_overwritten(self):
        defaults = {"foo": {"bar": "baz"}}
        overrides = {"foo": {"notbar": "notbaz"}}
        c = Config(defaults=defaults, overrides=overrides)
        assert c.foo.notbar == "notbaz"
        assert c.foo.bar == "baz"

    def test_is_iterable_like_dict(self):
        c = Config(defaults={"a": 1, "b": 2})
        assert set(c.keys()) == {"a", "b"}
        assert set(list(c)) == {"a", "b"}

    def test_supports_readonly_dict_protocols(self):
        c = Config(defaults={"foo": "bar"})
        c2 = Config(defaults={"foo": "bar"})
        assert "foo" in c
        assert "foo" in c2
        assert c == c2
        assert len(c) == 1
        assert c.get("foo") == "bar"
        assert list(c.items()) == [("foo", "bar")]
        assert list(c.keys()) == ["foo"]
        assert list(c.values()) == ["bar"]


class TestRuntimeLoadingOfDefaultsAndOverrides:
    """Test runtime loading of defaults and overrides."""

    def test_defaults_can_be_given_via_method(self):
        c = Config()
        assert "foo" not in c
        c.load_defaults({"foo": "bar"})
        assert c.foo == "bar"

    def test_defaults_can_skip_merging(self):
        c = Config()
        c.load_defaults({"foo": "bar"}, merge=False)
        assert "foo" not in c
        c.merge()
        assert c.foo == "bar"

    def test_overrides_can_be_given_via_method(self):
        c = Config(defaults={"foo": "bar"})
        assert c.foo == "bar"
        c.load_overrides({"foo": "notbar"})
        assert c.foo == "notbar"

    def test_overrides_can_skip_merging(self):
        c = Config()
        c.load_overrides({"foo": "bar"}, merge=False)
        assert "foo" not in c
        c.merge()
        assert c.foo == "bar"


class TestDeletionMethods:
    """Test dict-like deletion methods."""

    def test_pop(self):
        c = Config(defaults={"foo": "bar"})
        assert c.pop("foo") == "bar"
        assert c == {}
        assert c.pop("wut", "fine then") == "fine then"
        c.nested = {"leafkey": "leafval"}
        assert c.nested.pop("leafkey") == "leafval"
        assert c == {"nested": {}}

    def test_delitem(self):
        c = Config(defaults={"foo": "bar"})
        del c["foo"]
        assert c == {}
        c.nested = {"leafkey": "leafval"}
        del c.nested["leafkey"]
        assert c == {"nested": {}}

    def test_delattr(self):
        c = Config(defaults={"foo": "bar"})
        del c.foo
        assert c == {}
        c.nested = {"leafkey": "leafval"}
        del c.nested.leafkey
        assert c == {"nested": {}}

    def test_clear(self):
        c = Config(defaults={"foo": "bar"})
        c.clear()
        assert c == {}
        c.nested = {"leafkey": "leafval"}
        c.nested.clear()
        assert c == {"nested": {}}

    def test_popitem(self):
        c = Config(defaults={"foo": "bar"})
        assert c.popitem() == ("foo", "bar")
        assert c == {}
        c.nested = {"leafkey": "leafval"}
        assert c.nested.popitem() == ("leafkey", "leafval")
        assert c == {"nested": {}}


class TestModificationMethods:
    """Test dict-like modification methods."""

    def test_setitem(self):
        c = Config(defaults={"foo": "bar"})
        c["foo"] = "notbar"
        assert c.foo == "notbar"
        del c["foo"]
        c["nested"] = {"leafkey": "leafval"}
        assert c == {"nested": {"leafkey": "leafval"}}

    def test_setdefault(self):
        c = Config({"foo": "bar", "nested": {"leafkey": "leafval"}})
        assert c.setdefault("foo") == "bar"
        assert c.nested.setdefault("leafkey") == "leafval"
        assert c.setdefault("notfoo", "notbar") == "notbar"
        assert c.notfoo == "notbar"
        nested = c.nested.setdefault("otherleaf", "otherval")
        assert nested == "otherval"
        assert c.nested.otherleaf == "otherval"

    def test_update(self):
        c = Config(defaults={"foo": "bar", "nested": {"leafkey": "leafval"}})
        c.update({"foo": "notbar"})
        assert c.foo == "notbar"
        c.nested.update({"leafkey": "otherval"})
        assert c.nested.leafkey == "otherval"
        c.update()
        expected = {"foo": "notbar", "nested": {"leafkey": "otherval"}}
        assert c == expected
        c.update(foo="otherbar")
        assert c.foo == "otherbar"
        c.nested.update([("leafkey", "yetanotherval"), ("newleaf", "turnt")])
        assert c.nested.leafkey == "yetanotherval"
        assert c.nested.newleaf == "turnt"


class TestMiscBasicAPI:
    """Miscellaneous basic API tests."""

    def test_reinstatement_of_deleted_values_works_ok(self):
        c = Config(defaults={"foo": "bar"})
        assert c.foo == "bar"
        del c["foo"]
        assert "foo" not in c
        assert len(c) == 0
        c.foo = "formerly bar"
        assert c.foo == "formerly bar"

    def test_deleting_parent_keys_of_deleted_keys_subsumes_them(self):
        c = Config({"foo": {"bar": "biz"}})
        del c.foo["bar"]
        del c.foo
        assert c._deletions == {"foo": None}

    def test_supports_mutation_via_attribute_access(self):
        c = Config({"foo": "bar"})
        assert c.foo == "bar"
        c.foo = "notbar"
        assert c.foo == "notbar"
        assert c["foo"] == "notbar"

    def test_supports_nested_mutation_via_attribute_access(self):
        c = Config({"foo": {"bar": "biz"}})
        assert c.foo.bar == "biz"
        c.foo.bar = "notbiz"
        assert c.foo.bar == "notbiz"
        assert c["foo"]["bar"] == "notbiz"

    def test_real_attrs_and_methods_win_over_attr_proxying(self):
        class MyConfig(Config):
            myattr = None

            def mymethod(self):
                return 7

        c = MyConfig({"myattr": "foo", "mymethod": "bar"})
        assert c.myattr is None
        assert c["myattr"] == "foo"
        c.myattr = "notfoo"
        assert c.myattr == "notfoo"
        assert c["myattr"] == "foo"
        assert callable(c.mymethod)
        assert c.mymethod() == 7
        assert c["mymethod"] == "bar"

        def monkeys():
            return 13

        c.mymethod = monkeys
        assert c.mymethod() == 13
        assert c["mymethod"] == "bar"

    def test_config_itself_stored_as_private_name(self):
        c = Config()
        c["foo"] = {"bar": "baz"}
        c["whatever"] = {"config": "myconfig"}
        assert c.foo.bar == "baz"
        assert c.whatever.config == "myconfig"

    def test_inherited_real_attrs_also_win_over_config_keys(self):
        class MyConfigParent(Config):
            parent_attr = 17

        class MyConfig(MyConfigParent):
            pass

        c = MyConfig()
        assert c.parent_attr == 17
        c.parent_attr = 33
        oops = "Oops! Looks like config won over real attr!"
        assert "parent_attr" not in c, oops
        assert c.parent_attr == 33
        c["parent_attr"] = "fifteen"
        assert c.parent_attr == 33
        assert c["parent_attr"] == "fifteen"

    def test_nonexistent_attrs_can_be_set_to_create_new_top_level_configs(self):
        c = Config()
        c.some_setting = "some_value"
        assert c["some_setting"] == "some_value"

    def test_nonexistent_attr_setting_works_nested_too(self):
        c = Config()
        c.a_nest = {}
        assert c["a_nest"] == {}
        c.a_nest.an_egg = True
        assert c["a_nest"]["an_egg"]

    def test_string_display(self):
        config = Config(defaults={"foo": "bar"})
        assert repr(config) == "<Config: {'foo': 'bar'}>"

    def test_merging_does_not_wipe_user_modifications_or_deletions(self):
        c = Config({"foo": {"bar": "biz"}, "error": True})
        c.foo.bar = "notbiz"
        del c["error"]
        assert c["foo"]["bar"] == "notbiz"
        assert "error" not in c
        c.merge()
        assert c["foo"]["bar"] == "notbiz"
        assert "error" not in c


class TestConfigFileLoading:
    """Test configuration file loading."""

    def test_system_global(self):
        for type_ in TYPES:
            config = _load("system_prefix", type_, lazy=True)
            assert "outer" not in config
            config.load_system()
            assert config.outer.inner.hooray == type_

    def test_system_can_skip_merging(self):
        config = _load("system_prefix", "yml", lazy=True)
        assert "outer" not in config._system
        assert "outer" not in config
        config.load_system(merge=False)
        assert "outer" in config._system
        assert "outer" not in config

    def test_user_specific(self):
        for type_ in TYPES:
            config = _load("user_prefix", type_, lazy=True)
            assert "outer" not in config
            config.load_user()
            assert config.outer.inner.hooray == type_

    def test_user_can_skip_merging(self):
        config = _load("user_prefix", "yml", lazy=True)
        assert "outer" not in config._user
        assert "outer" not in config
        config.load_user(merge=False)
        assert "outer" in config._user
        assert "outer" not in config

    def test_project_specific(self):
        for type_ in TYPES:
            c = Config(project_location=join(CONFIGS_PATH, type_))
            assert "outer" not in c
            c.load_project()
            assert c.outer.inner.hooray == type_

    def test_project_can_skip_merging(self):
        config = Config(project_location=join(CONFIGS_PATH, "yml"), lazy=True)
        assert "outer" not in config._project
        assert "outer" not in config
        config.load_project(merge=False)
        assert "outer" in config._project
        assert "outer" not in config

    def test_loads_no_project_specific_file_if_no_project_location_given(self):
        c = Config()
        assert c._project_path is None
        c.load_project()
        assert list(c._project.keys()) == []
        defaults = ["tasks", "run", "runners", "sudo", "timeouts"]
        assert set(c.keys()) == set(defaults)

    def test_project_location_can_be_set_after_init(self):
        c = Config()
        assert "outer" not in c
        c.set_project_location(join(CONFIGS_PATH, "yml"))
        c.load_project()
        assert c.outer.inner.hooray == "yml"

    def test_runtime_conf_via_cli_flag(self):
        c = Config(runtime_path=join(CONFIGS_PATH, "yaml", "invoke.yaml"))
        c.load_runtime()
        assert c.outer.inner.hooray == "yaml"

    def test_runtime_can_skip_merging(self):
        path = join(CONFIGS_PATH, "yaml", "invoke.yaml")
        config = Config(runtime_path=path, lazy=True)
        assert "outer" not in config._runtime
        assert "outer" not in config
        config.load_runtime(merge=False)
        assert "outer" in config._runtime
        assert "outer" not in config

    def test_unknown_suffix_in_runtime_path_raises_useful_error(self):
        c = Config(runtime_path=join(CONFIGS_PATH, "screw.ini"))
        with pytest.raises(UnknownFileType):
            c.load_runtime()

    def test_python_modules_dont_load_special_vars(self):
        c = _load("system_prefix", "python")
        assert c.outer.inner.hooray == "python"
        for special in ("builtins", "file", "package", "name", "doc"):
            assert "__{}__".format(special) not in c

    def test_python_modules_except_usefully_on_unpicklable_modules(self):
        c = Config()
        c.set_runtime_path(join(support, "has_modules.py"))
        expected = r"'os' is a module.*giving a tasks file.*mistake"
        with pytest.raises(UnpicklableConfigMember, match=expected):
            c.load_runtime(merge=False)

    @patch("invoke.config.debug")
    def test_nonexistent_files_are_skipped_and_logged(self, mock_debug):
        c = Config()
        c._load_yml = Mock(side_effect=IOError(2, "aw nuts"))
        c.set_runtime_path("is-a.yml")
        c.load_runtime()
        mock_debug.assert_any_call("Didn't see any is-a.yml, skipping.")

    def test_non_missing_file_IOErrors_are_raised(self):
        c = Config()
        c._load_yml = Mock(side_effect=IOError(17, "uh, what?"))
        c.set_runtime_path("is-a.yml")
        with pytest.raises(IOError):
            c.load_runtime()


class TestCollectionLevelConfigLoading:
    """Test collection-level config loading."""

    def test_performed_explicitly_and_directly(self):
        c = Config()
        assert "foo" not in c
        c.load_collection({"foo": "bar"})
        assert c.foo == "bar"

    def test_merging_can_be_deferred(self):
        c = Config()
        assert "foo" not in c._collection
        assert "foo" not in c
        c.load_collection({"foo": "bar"}, merge=False)
        assert "foo" in c._collection
        assert "foo" not in c


class TestComparisonAndHashing:
    """Test comparison and hashing behavior."""

    def test_comparison_looks_at_merged_config(self):
        c1 = Config(defaults={"foo": {"bar": "biz"}})
        c2 = Config(defaults={}, overrides={"foo": {"bar": "biz"}})
        assert c1 is not c2
        assert c1._defaults != c2._defaults
        assert c1 == c2

    def test_allows_comparison_with_real_dicts(self):
        c = Config({"foo": {"bar": "biz"}})
        assert c["foo"] == {"bar": "biz"}

    def test_is_explicitly_not_hashable(self):
        with pytest.raises(TypeError):
            hash(Config())


class TestEnvVars:
    """Test environment variable handling."""

    def test_base_case_defaults_to_INVOKE_prefix(self):
        os.environ["INVOKE_FOO"] = "bar"
        c = Config(defaults={"foo": "notbar"})
        c.load_shell_env()
        assert c.foo == "bar"

    def test_non_predeclared_settings_do_not_get_consumed(self):
        os.environ["INVOKE_HELLO"] = "is it me you're looking for?"
        c = Config()
        c.load_shell_env()
        assert "HELLO" not in c
        assert "hello" not in c

    def test_underscores_top_level(self):
        os.environ["INVOKE_FOO_BAR"] = "biz"
        c = Config(defaults={"foo_bar": "notbiz"})
        c.load_shell_env()
        assert c.foo_bar == "biz"

    def test_underscores_nested(self):
        os.environ["INVOKE_FOO_BAR"] = "biz"
        c = Config(defaults={"foo": {"bar": "notbiz"}})
        c.load_shell_env()
        assert c.foo.bar == "biz"

    def test_both_types_of_underscores_mixed(self):
        os.environ["INVOKE_FOO_BAR_BIZ"] = "baz"
        c = Config(defaults={"foo_bar": {"biz": "notbaz"}})
        c.load_shell_env()
        assert c.foo_bar.biz == "baz"

    def test_ambiguous_underscores_dont_guess(self):
        os.environ["INVOKE_FOO_BAR"] = "biz"
        c = Config(defaults={"foo_bar": "wat", "foo": {"bar": "huh"}})
        with pytest.raises(AmbiguousEnvVar):
            c.load_shell_env()


class TestTypeCasting:
    """Test environment variable type casting."""

    def test_strings_replaced_with_env_value(self):
        os.environ["INVOKE_FOO"] = "myvalue"
        c = Config(defaults={"foo": "myoldvalue"})
        c.load_shell_env()
        assert c.foo == "myvalue"
        assert isinstance(c.foo, str)

    def test_None_replaced(self):
        os.environ["INVOKE_FOO"] = "something"
        c = Config(defaults={"foo": None})
        c.load_shell_env()
        assert c.foo == "something"

    def test_booleans(self):
        for input_, result in (
            ("0", False),
            ("1", True),
            ("", False),
            ("meh", True),
            ("false", True),
        ):
            os.environ["INVOKE_FOO"] = input_
            c = Config(defaults={"foo": bool()})
            c.load_shell_env()
            assert c.foo == result

    def test_boolean_type_inputs_with_non_boolean_defaults(self):
        for input_ in ("0", "1", "", "meh", "false"):
            os.environ["INVOKE_FOO"] = input_
            c = Config(defaults={"foo": "bar"})
            c.load_shell_env()
            assert c.foo == input_

    def test_numeric_types_become_casted(self):
        tests = [
            (int, "5", 5),
            (float, "5.5", 5.5),
        ]
        for old, new_, result in tests:
            os.environ["INVOKE_FOO"] = new_
            c = Config(defaults={"foo": old()})
            c.load_shell_env()
            assert c.foo == result

    def test_arbitrary_types_work_too(self):
        os.environ["INVOKE_FOO"] = "whatever"

        class Meh:
            def __init__(self, thing=None):
                pass

        old_obj = Meh()
        c = Config(defaults={"foo": old_obj})
        c.load_shell_env()
        assert isinstance(c.foo, Meh)
        assert c.foo is not old_obj


class TestUncastableTypes:
    """Test uncastable type handling."""

    def _uncastable_type(self, default):
        os.environ["INVOKE_FOO"] = "stuff"
        c = Config(defaults={"foo": default})
        with pytest.raises(UncastableEnvVar):
            c.load_shell_env()

    def test_lists(self):
        self._uncastable_type(["a", "list"])

    def test_tuples(self):
        self._uncastable_type(("a", "tuple"))


class TestHierarchy:
    """Test config hierarchy."""

    def test_collection_overrides_defaults(self):
        c = Config(defaults={"nested": {"setting": "default"}})
        c.load_collection({"nested": {"setting": "collection"}})
        assert c.nested.setting == "collection"

    def test_systemwide_overrides_collection(self):
        c = Config(system_prefix=join(CONFIGS_PATH, "yaml/"))
        c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
        assert c.outer.inner.hooray == "yaml"

    def test_user_overrides_systemwide(self):
        c = Config(
            system_prefix=join(CONFIGS_PATH, "yaml/"),
            user_prefix=join(CONFIGS_PATH, "json/"),
        )
        assert c.outer.inner.hooray == "json"

    def test_user_overrides_collection(self):
        c = Config(user_prefix=join(CONFIGS_PATH, "json/"))
        c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
        assert c.outer.inner.hooray == "json"

    def test_project_overrides_user(self):
        c = Config(
            user_prefix=join(CONFIGS_PATH, "json/"),
            project_location=join(CONFIGS_PATH, "yaml"),
        )
        c.load_project()
        assert c.outer.inner.hooray == "yaml"

    def test_project_overrides_systemwide(self):
        c = Config(
            system_prefix=join(CONFIGS_PATH, "json/"),
            project_location=join(CONFIGS_PATH, "yaml"),
        )
        c.load_project()
        assert c.outer.inner.hooray == "yaml"

    def test_project_overrides_collection(self):
        c = Config(project_location=join(CONFIGS_PATH, "yaml"))
        c.load_project()
        c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
        assert c.outer.inner.hooray == "yaml"

    def test_env_vars_override_project(self):
        os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
        c = Config(project_location=join(CONFIGS_PATH, "yaml"))
        c.load_project()
        c.load_shell_env()
        assert c.outer.inner.hooray == "env"

    def test_env_vars_override_user(self):
        os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
        c = Config(user_prefix=join(CONFIGS_PATH, "yaml/"))
        c.load_shell_env()
        assert c.outer.inner.hooray == "env"

    def test_env_vars_override_systemwide(self):
        os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
        c = Config(system_prefix=join(CONFIGS_PATH, "yaml/"))
        c.load_shell_env()
        assert c.outer.inner.hooray == "env"

    def test_env_vars_override_collection(self):
        os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
        c = Config()
        c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
        c.load_shell_env()
        assert c.outer.inner.hooray == "env"

    def test_runtime_overrides_env_vars(self):
        os.environ["INVOKE_OUTER_INNER_HOORAY"] = "env"
        c = Config(runtime_path=join(CONFIGS_PATH, "json", "invoke.json"))
        c.load_runtime()
        c.load_shell_env()
        assert c.outer.inner.hooray == "json"

    def test_runtime_overrides_project(self):
        c = Config(
            runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
            project_location=join(CONFIGS_PATH, "yaml"),
        )
        c.load_runtime()
        c.load_project()
        assert c.outer.inner.hooray == "json"

    def test_runtime_overrides_user(self):
        c = Config(
            runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
            user_prefix=join(CONFIGS_PATH, "yaml/"),
        )
        c.load_runtime()
        assert c.outer.inner.hooray == "json"

    def test_runtime_overrides_systemwide(self):
        c = Config(
            runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
            system_prefix=join(CONFIGS_PATH, "yaml/"),
        )
        c.load_runtime()
        assert c.outer.inner.hooray == "json"

    def test_runtime_overrides_collection(self):
        c = Config(runtime_path=join(CONFIGS_PATH, "json", "invoke.json"))
        c.load_collection({"outer": {"inner": {"hooray": "defaults"}}})
        c.load_runtime()
        assert c.outer.inner.hooray == "json"

    def test_cli_overrides_override_all(self):
        c = Config(
            overrides={"outer": {"inner": {"hooray": "overrides"}}},
            runtime_path=join(CONFIGS_PATH, "json", "invoke.json"),
        )
        c.load_runtime()
        assert c.outer.inner.hooray == "overrides"

    def test_yaml_prevents_yml_json_or_python(self):
        c = Config(system_prefix=join(CONFIGS_PATH, "all-four/"))
        assert "json-only" not in c
        assert "python_only" not in c
        assert "yml-only" not in c
        assert "yaml-only" in c
        assert c.shared == "yaml-value"

    def test_yml_prevents_json_or_python(self):
        c = Config(system_prefix=join(CONFIGS_PATH, "three-of-em/"))
        assert "json-only" not in c
        assert "python_only" not in c
        assert "yml-only" in c
        assert c.shared == "yml-value"

    def test_json_prevents_python(self):
        c = Config(system_prefix=join(CONFIGS_PATH, "json-and-python/"))
        assert "python_only" not in c
        assert "json-only" in c
        assert c.shared == "json-value"


class TestClone:
    """Test Config.clone() behavior."""

    def test_preserves_basic_members(self):
        c1 = Config(
            defaults={"key": "default"},
            overrides={"key": "override"},
            system_prefix="global",
            user_prefix="user",
            project_location="project",
            runtime_path="runtime.yaml",
        )
        c2 = c1.clone()
        assert c2._defaults == c1._defaults
        assert c2._defaults is not c1._defaults
        assert c2._overrides == c1._overrides
        assert c2._overrides is not c1._overrides
        assert c2._system_prefix == c1._system_prefix
        assert c2._user_prefix == c1._user_prefix
        assert c2._project_prefix == c1._project_prefix
        assert c2.prefix == c1.prefix
        assert c2.file_prefix == c1.file_prefix
        assert c2.env_prefix == c1.env_prefix
        assert c2._runtime_path == c1._runtime_path

    def test_preserves_merged_config(self):
        c = Config(defaults={"key": "default"}, overrides={"key": "override"})
        assert c.key == "override"
        assert c._defaults["key"] == "default"
        c2 = c.clone()
        assert c2.key == "override"
        assert c2._defaults["key"] == "default"
        assert c2._overrides["key"] == "override"

    def test_preserves_file_data(self):
        c = Config(system_prefix=join(CONFIGS_PATH, "yaml/"))
        assert c.outer.inner.hooray == "yaml"
        c2 = c.clone()
        assert c2.outer.inner.hooray == "yaml"
        assert c2._system == {"outer": {"inner": {"hooray": "yaml"}}}

    @patch.object(
        Config,
        "_load_yaml",
        return_value={"outer": {"inner": {"hooray": "yaml"}}},
    )
    def test_does_not_reload_file_data(self, load_yaml):
        path = join(CONFIGS_PATH, "yaml/")
        c = Config(system_prefix=path)
        c2 = c.clone()
        assert c2.outer.inner.hooray == "yaml"
        calls = load_yaml.call_args_list
        my_call = call("{}invoke.yaml".format(path))
        try:
            calls.remove(my_call)
            assert my_call not in calls
        except ValueError:
            err = "{} not found in {} even once!"
            assert False, err.format(my_call, calls)

    def test_preserves_env_data(self):
        os.environ["INVOKE_FOO"] = "bar"
        c = Config(defaults={"foo": "notbar"})
        c.load_shell_env()
        c2 = c.clone()
        assert c2.foo == "bar"

    def test_works_correctly_when_subclassed(self):
        class MyConfig(Config):
            pass

        c = MyConfig()
        assert isinstance(c, MyConfig)
        c2 = c.clone()
        assert isinstance(c2, MyConfig)


class TestCloneIntoKwarg:
    """Test clone 'into' kwarg."""

    def test_is_not_required(self):
        c = Config(defaults={"meh": "okay"})
        c2 = c.clone()
        assert c2.meh == "okay"

    def test_resulting_clones_are_typed_as_new_class(self):
        class MyConfig(Config):
            pass

        c = Config()
        c2 = c.clone(into=MyConfig)
        assert type(c2) is MyConfig

    def test_non_conflicting_values_are_merged(self):
        class MyConfig(Config):
            @staticmethod
            def global_defaults():
                orig = Config.global_defaults()
                orig["new"] = {"data": "ohai"}
                return orig

        c = Config(defaults={"other": {"data": "hello"}})
        c["runtime"] = {"modification": "sup"}
        c2 = c.clone(into=MyConfig)
        assert c2.new.data == "ohai"
        assert c2.other.data == "hello"
        assert c2.runtime.modification == "sup"


class TestDeepCopy:
    """Test clone deep copy behavior."""

    def test_does_not_deepcopy(self):
        c = Config(
            defaults={
                "oh": {"dear": {"god": object()}},
                "shallow": {"objects": ["copy", "okay"]},
                "deep": {"cannot": ["have", {"everything": "we want"}]},
            }
        )
        c2 = c.clone()
        assert c is not c2, "Clone had same identity as original!"
        assert c.oh is not c2.oh, "Top level key had same identity!"
        assert c.oh.dear is not c2.oh.dear, "Midlevel key had same identity!"
        err = "Leaf object() had same identity!"
        assert c.oh.dear.god is not c2.oh.dear.god, err
        assert c.shallow.objects == c2.shallow.objects
        err = "Shallow list had same identity!"
        assert c.shallow.objects is not c2.shallow.objects, err
        err = "Huh, a deeply nested dict-in-a-list had different identity?"
        assert c.deep.cannot[1] is c2.deep.cannot[1], err
        err = "Huh, a deeply nested dict-in-a-list value had different identity?"
        assert c.deep.cannot[1]["everything"] is c2.deep.cannot[1]["everything"], err


class TestPickle:
    """Test pickling behavior."""

    def test_can_be_pickled(self):
        c = Config(overrides={"foo": {"bar": {"biz": ["baz", "buzz"]}}})
        c2 = pickle.loads(pickle.dumps(c))
        assert c == c2
        assert c is not c2
        assert c.foo.bar.biz is not c2.foo.bar.biz
