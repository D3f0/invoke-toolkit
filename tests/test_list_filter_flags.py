"""Tests for --list-tasks and --list-plugins filter flags."""

import json


from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram


# ---------------------------------------------------------------------------
# Shared task/collection factories
# ---------------------------------------------------------------------------


@task()
def main_task_a(ctx: Context):
    """Main task A"""


@task()
def main_task_b(ctx: Context):
    """Main task B"""


@task()
def plugin_task_x(ctx: Context):
    """Plugin task X"""


@task()
def plugin_task_y(ctx: Context):
    """Plugin task Y"""


def _make_collection_with_plugins() -> tuple[ToolkitCollection, set[str]]:
    """
    Build a ToolkitCollection that looks like 'tasks.py + two plugin sub-collections'.
    Returns the collection and the set of plugin sub-collection names.
    """
    coll = ToolkitCollection("root")
    coll.add_task(main_task_a)
    coll.add_task(main_task_b)

    plugin_coll = ToolkitCollection("myplugin")
    plugin_coll.add_task(plugin_task_x)
    plugin_coll.add_task(plugin_task_y)
    coll.add_collection(plugin_coll, name="myplugin")

    another_plugin = ToolkitCollection("otherplugin")
    coll.add_collection(another_plugin, name="otherplugin")

    return coll, {"myplugin", "otherplugin"}


def _program_with_plugins(
    plugin_names: set[str] | None = None,
) -> tuple[TestingToolkitProgram, ToolkitCollection]:
    """Return a configured TestingToolkitProgram with a plugin-aware collection."""
    coll, plugin_set = _make_collection_with_plugins()
    p = TestingToolkitProgram(namespace=coll)
    if plugin_names is None:
        p._plugin_collection_names = plugin_set
    else:
        p._plugin_collection_names = plugin_names
    return p, coll


# ---------------------------------------------------------------------------
# --list-tasks
# ---------------------------------------------------------------------------


def test_list_tasks_shows_main_tasks(capsys, suppress_stderr_logging):
    """--list-tasks output contains the direct main tasks."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-tasks", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    task_names = {t["name"] for t in data["tasks"]}
    assert "main-task-a" in task_names
    assert "main-task-b" in task_names


def test_list_tasks_excludes_plugin_collections(capsys, suppress_stderr_logging):
    """--list-tasks must NOT include plugin sub-collections."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-tasks", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    coll_names = {c["name"] for c in data.get("collections", [])}
    assert "myplugin" not in coll_names
    assert "otherplugin" not in coll_names


def test_list_tasks_flat_format(capsys, suppress_stderr_logging):
    """--list-tasks works with the default flat format (no JSON)."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-tasks"])
    out, _ = capsys.readouterr()
    assert "main-task-a" in out
    assert "main-task-b" in out
    assert "myplugin" not in out


def test_list_tasks_no_plugins_registered(capsys, suppress_stderr_logging):
    """--list-tasks when there are no plugins still shows the main tasks."""
    coll = ToolkitCollection("root")
    coll.add_task(main_task_a)
    p = TestingToolkitProgram(namespace=coll)
    # _plugin_collection_names starts empty (no plugins)
    p.run(["", "--list-tasks", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    task_names = {t["name"] for t in data["tasks"]}
    assert "main-task-a" in task_names


def test_list_tasks_preserves_non_plugin_subcollections(
    capsys, suppress_stderr_logging
):
    """Non-plugin sub-collections (e.g. from tasks.py namespace) are kept by --list-tasks."""
    coll = ToolkitCollection("root")
    coll.add_task(main_task_a)

    sub = ToolkitCollection("utils")
    sub.add_task(main_task_b)
    coll.add_collection(sub, name="utils")

    plugin_coll = ToolkitCollection("myplugin")
    plugin_coll.add_task(plugin_task_x)
    coll.add_collection(plugin_coll, name="myplugin")

    p = TestingToolkitProgram(namespace=coll)
    p._plugin_collection_names = {"myplugin"}

    p.run(["", "--list-tasks", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    coll_names = {c["name"] for c in data.get("collections", [])}
    assert "utils" in coll_names
    assert "myplugin" not in coll_names


# ---------------------------------------------------------------------------
# --list-plugins
# ---------------------------------------------------------------------------


def test_list_plugins_shows_plugin_collections(capsys, suppress_stderr_logging):
    """--list-plugins output contains the plugin sub-collections."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-plugins", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    coll_names = {c["name"] for c in data.get("collections", [])}
    assert "myplugin" in coll_names
    assert "otherplugin" in coll_names


def test_list_plugins_excludes_main_tasks(capsys, suppress_stderr_logging):
    """--list-plugins must NOT include the direct main tasks."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-plugins", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    task_names = {t["name"] for t in data.get("tasks", [])}
    assert "main-task-a" not in task_names
    assert "main-task-b" not in task_names


def test_list_plugins_flat_format(capsys, suppress_stderr_logging):
    """--list-plugins works with the default flat format."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-plugins"])
    out, _ = capsys.readouterr()
    assert "myplugin" in out
    assert "main-task-a" not in out


def test_list_plugins_no_plugins_exits_with_message(capsys, suppress_stderr_logging):
    """--list-plugins when there are no plugins exits with a clear message."""
    coll = ToolkitCollection("root")
    coll.add_task(main_task_a)
    p = TestingToolkitProgram(namespace=coll)
    # _plugin_collection_names is empty — no plugins loaded
    p.run(["", "--list-plugins"])
    # run(..., exit=False) so no sys.exit — just check stderr for the message
    _, err = capsys.readouterr()
    assert "No plugin collections found" in err


# ---------------------------------------------------------------------------
# Mutual exclusion sanity (using both flags at once: first one wins)
# ---------------------------------------------------------------------------


def test_list_tasks_takes_precedence_over_list_plugins(capsys, suppress_stderr_logging):
    """When both --list-tasks and --list-plugins are given, --list-tasks runs first."""
    p, _ = _program_with_plugins()
    p.run(["", "--list-tasks", "--list-plugins", "--list-format", "json"])
    out, _ = capsys.readouterr()
    data = json.loads(out)
    # Should behave like --list-tasks
    task_names = {t["name"] for t in data["tasks"]}
    assert "main-task-a" in task_names
    coll_names = {c["name"] for c in data.get("collections", [])}
    assert "myplugin" not in coll_names
