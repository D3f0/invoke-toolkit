import ast
import sys
from pathlib import Path
from textwrap import dedent

from invoke_toolkit.collections import ToolkitCollection


def test_collection_load_submodules(monkeypatch, tmp_path: Path):
    """
    Creates some module in a temporary directory and tries to import from that location
    """
    ns = ToolkitCollection()
    code_module_for_tasks = dedent(
        """
    from invoke_toolkit import task

    @task()
    def a_task(ctx):
        ...
    """
    )

    def create_module(folder: Path, name: str, code=code_module_for_tasks):
        file_to_write_to = folder / name
        file_to_write_to.write_text(code)
        return file_to_write_to

    ast.parse(code_module_for_tasks)
    # Simulate modules
    to_import_p: Path = tmp_path / "to_import"
    to_import_p.mkdir()
    tasks_p: Path = to_import_p / "tasks"
    tasks_p.mkdir()
    # Create the package manager for to_import.tasks (the __init__.py)
    (tasks_p / "__init__.py").write_text("")
    create_module(tasks_p, "mod1.py")
    create_module(tasks_p, "mod2.py")

    sys.path.append(str(tmp_path))

    ns.add_collections_from_namespace("to_import.tasks")

    found_collections = ns.collections
    assert set(found_collections.keys()) == {"mod1", "mod2"}


def test_flat_task_discovery_from_namespace(monkeypatch, tmp_path: Path):
    """
    Test that add_flat_tasks_from_namespace flattens all tasks from submodules
    into the collection without module hierarchy, while keeping the collection name.
    """
    ns = ToolkitCollection("test_pkg")
    code_module_for_tasks = dedent(
        """
        from invoke_toolkit import task

        @task()
        def a_task(ctx):
            ...
        """
    )

    def create_module(folder: Path, name: str, code=code_module_for_tasks):
        file_to_write_to = folder / name
        file_to_write_to.write_text(code)
        return file_to_write_to

    # Simulate modules
    to_import_p: Path = tmp_path / "to_import_flat"
    to_import_p.mkdir()
    tasks_p: Path = to_import_p / "tasks"
    tasks_p.mkdir()
    # Create the package manager for to_import.tasks (the __init__.py)
    (tasks_p / "__init__.py").write_text("")
    create_module(
        tasks_p, "mod1.py", code_module_for_tasks.replace("a_task", "task_one")
    )
    create_module(
        tasks_p, "mod2.py", code_module_for_tasks.replace("a_task", "task_two")
    )

    sys.path.append(str(tmp_path))

    # Use flat discovery instead of nested collections
    ns.add_flat_tasks_from_namespace("to_import_flat.tasks")

    # Tasks should be directly in collection, not in module subcollections
    found_tasks = ns.tasks
    assert "task-one" in found_tasks, (
        f"task-one not found in tasks: {found_tasks.keys()}"
    )
    assert "task-two" in found_tasks, (
        f"task-two not found in tasks: {found_tasks.keys()}"
    )
    # Verify no subcollections were created (tasks are flattened into this collection)
    assert len(ns.collections) == 0, (
        f"Unexpected collections found: {ns.collections.keys()}"
    )


def test_load_local_tasks(tmp_path: Path):
    """
    Test loading local_tasks.py from a directory
    """
    ns = ToolkitCollection()

    # Create local_tasks.py
    local_tasks_code = dedent(
        """
        from invoke_toolkit import task

        @task()
        def my_task(ctx):
            '''A local task'''
            pass

        @task()
        def another_task(ctx):
            '''Another local task'''
            pass
        """
    )
    local_tasks_file = tmp_path / "local_tasks.py"
    local_tasks_file.write_text(local_tasks_code)

    # Load local tasks
    ns.load_local_tasks(search_path=tmp_path)

    # Verify the local collection was created
    assert "local" in ns.collections
    local_col = ns.collections["local"]

    # Verify tasks are in the local collection
    assert "my-task" in local_col.tasks
    assert "another-task" in local_col.tasks


def test_load_local_tasks_missing_file(tmp_path: Path):
    """
    Test that load_local_tasks handles missing local_tasks.py gracefully
    """
    ns = ToolkitCollection()

    # Try to load from directory with no local_tasks.py
    ns.load_local_tasks(search_path=tmp_path)

    # Verify no local collection was created
    assert "local" not in ns.collections


def test_load_local_tasks_with_default_path(tmp_path: Path, monkeypatch):
    """
    Test loading local_tasks.py from current directory by default
    """
    ns = ToolkitCollection()

    # Create local_tasks.py in a temporary directory
    local_tasks_code = dedent(
        """
        from invoke_toolkit import task

        @task()
        def local_default_task(ctx):
            '''A local task'''
            pass
        """
    )
    local_tasks_file = tmp_path / "local_tasks.py"
    local_tasks_file.write_text(local_tasks_code)

    # Change to the temporary directory
    monkeypatch.chdir(tmp_path)

    # Load local tasks without specifying path
    ns.load_local_tasks()

    # Verify the local collection was created
    assert "local" in ns.collections
    local_col = ns.collections["local"]

    # Verify task is in the local collection
    assert "local-default-task" in local_col.tasks


def test_load_local_tasks_without_main_tasks(tmp_path: Path):
    """
    Test that local tasks can be loaded even when no main tasks.py exists
    """
    ns = ToolkitCollection()

    # Create only local_tasks.py (no tasks.py)
    local_tasks_code = dedent(
        """
        from invoke_toolkit import task

        @task()
        def standalone_task(ctx):
            '''A standalone local task'''
            pass
        """
    )
    local_tasks_file = tmp_path / "local_tasks.py"
    local_tasks_file.write_text(local_tasks_code)

    # Load local tasks
    ns.load_local_tasks(search_path=tmp_path)

    # Verify the local collection was created
    assert "local" in ns.collections
    local_col = ns.collections["local"]

    # Verify task is in the local collection
    assert "standalone-task" in local_col.tasks


def test_load_local_tasks_from_multiple_directories_without_module_collision(
    tmp_path: Path,
):
    """Loading local task files from different directories keeps both modules distinct."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "local_tasks.py").write_text(
        "from invoke_toolkit import task\n\n@task()\ndef first_task(ctx):\n    pass\n"
    )
    (second / "local_tasks.py").write_text(
        "from invoke_toolkit import task\n\n@task()\ndef second_task(ctx):\n    pass\n"
    )

    local_module_names_before = {
        name for name in sys.modules if name.startswith("_invoke_toolkit_local_tasks_")
    }
    first_collection = ToolkitCollection()
    second_collection = ToolkitCollection()
    first_collection.load_local_tasks(search_path=first)
    second_collection.load_local_tasks(search_path=second)

    assert "first-task" in first_collection.collections["local"].tasks
    assert "second-task" in second_collection.collections["local"].tasks
    local_module_names_after = {
        name for name in sys.modules if name.startswith("_invoke_toolkit_local_tasks_")
    }
    assert len(local_module_names_after - local_module_names_before) == 2
