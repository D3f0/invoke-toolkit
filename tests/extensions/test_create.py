from pathlib import Path

import pytest

from invoke_toolkit.context.context import ToolkitContext
from invoke_toolkit.testing import TestingToolkitProgram


def test_new_script(
    capsys: pytest.CaptureFixture,
    tmp_path: Path,
    # task_in_tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Runs create.script extension collection
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()
    x.run(["", "-x", "create.script", "--name", "tasks.py"])
    # out, err = capsys.readouterr()
    current_files = {p.name: p for p in tmp_path.glob("*.py")}
    assert "tasks.py" in current_files
    # script_content = current_files["tasks.py"].read_text()
    script_execution = ctx.run("uv run tasks.py hello-world", warn=True)
    assert script_execution.stdout.strip() == "hello world"


def test_new_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Tests that create.package generates a valid package with entry-point annotations
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()

    # Create a package
    package_name = "test-tasks-pkg"
    x.run(["", "-x", "create.package", "--name", package_name])

    # Verify the package directory exists
    pkg_dir = tmp_path / package_name
    assert pkg_dir.exists(), f"Package directory {pkg_dir} was not created"

    # Verify key files exist
    assert (pkg_dir / "pyproject.toml").exists(), "pyproject.toml not found"
    assert (pkg_dir / "README.md").exists(), "README.md not found"
    assert (pkg_dir / ".gitignore").exists(), ".gitignore not found"

    # Verify the source directory structure
    src_dir = pkg_dir / "src" / "test_tasks_pkg"
    assert src_dir.exists(), f"Source directory {src_dir} not found"
    assert (src_dir / "__init__.py").exists(), "__init__.py not found"
    assert (src_dir / "tasks.py").exists(), "tasks.py not found"

    # Verify pyproject.toml has entry-point
    pyproject_content = (pkg_dir / "pyproject.toml").read_text()
    assert "invoke_toolkit.collection" in pyproject_content, (
        "Entry-point group not found in pyproject.toml"
    )
    assert "test_tasks_pkg.tasks:ns" in pyproject_content, (
        "Collection entry-point not found in pyproject.toml"
    )

    # Verify tasks.py has the collection
    tasks_content = (src_dir / "tasks.py").read_text()
    assert "ns = ToolkitCollection" in tasks_content, (
        "Collection 'ns' not found in tasks.py"
    )
    assert "def hello" in tasks_content, "hello task not found in tasks.py"


def test_new_package_structure_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Validates the internal structure of a generated package.
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()

    # Create the package
    package_name = "my-sample-tasks"
    x.run(["", "-x", "create.package", "--name", package_name])

    pkg_dir = tmp_path / package_name
    pyproject_path = pkg_dir / "pyproject.toml"

    # Check pyproject.toml content
    pyproject_text = pyproject_path.read_text()

    # Should have project name
    assert f'name = "{package_name}"' in pyproject_text, (
        "Package name not set correctly in pyproject.toml"
    )

    # Should have invoke-toolkit as dependency
    assert "invoke-toolkit" in pyproject_text, "invoke-toolkit not in dependencies"

    # Check __init__.py content
    init_path = pkg_dir / "src" / "my_sample_tasks" / "__init__.py"
    init_text = init_path.read_text()

    # Should import the collection
    assert "from .tasks import ns" in init_text, (
        "Collection not imported in __init__.py"
    )


def test_new_package_callable_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Verifies that the generated package creates a valid collection module.
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()

    # Create the package
    x.run(["", "-x", "create.package", "--name", "importable-tasks"])

    pkg_dir = tmp_path / "importable-tasks"
    src_dir = pkg_dir / "src" / "importable_tasks"

    # Verify tasks.py has proper structure
    tasks_py = src_dir / "tasks.py"
    tasks_content = tasks_py.read_text()

    # Verify imports
    assert "from invoke_toolkit import" in tasks_content, (
        "Missing invoke_toolkit imports"
    )
    assert (
        "from invoke_toolkit.collections import ToolkitCollection" in tasks_content
    ), "Missing ToolkitCollection import"

    # Verify task definition
    assert "@task(" in tasks_content, "Missing @task decorator"
    assert "def hello(" in tasks_content, "Missing hello task function"

    # Verify collection creation
    assert "ns = ToolkitCollection(" in tasks_content, (
        "Missing collection instantiation"
    )

    # Verify __init__.py has proper exports
    init_py = src_dir / "__init__.py"
    init_content = init_py.read_text()

    assert "__version__" in init_content, "Missing __version__ in __init__.py"
    assert "from .tasks import ns" in init_content, "Missing ns export in __init__.py"
    assert "__all__" in init_content, "Missing __all__ in __init__.py"


def test_package_collection_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Integration test: verify that a package created with the template
    has the correct entry-point structure defined.
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()

    # Create a package using the template
    package_name = "discovery-test-pkg"
    x.run(["", "-x", "create.package", "--name", package_name])

    pkg_dir = tmp_path / package_name

    # Verify the entry-point is correctly defined in pyproject.toml
    pyproject_content = (pkg_dir / "pyproject.toml").read_text()
    assert '[project.entry-points."invoke_toolkit.collection"]' in pyproject_content, (
        "Entry-point group not defined in pyproject.toml"
    )

    collection_slug = "discovery_test_pkg"
    assert f'{collection_slug} = "{collection_slug}.tasks:ns"' in pyproject_content, (
        f"Entry-point '{collection_slug}' not found in pyproject.toml"
    )

    # Verify the package structure is complete for entry-point discovery
    # The entry-point system will discover and load this when the package is installed
    tasks_file = pkg_dir / "src" / collection_slug / "tasks.py"
    assert tasks_file.exists(), "tasks.py module not found"

    # Verify tasks.py exports the collection
    tasks_content = tasks_file.read_text()
    assert "ns = ToolkitCollection" in tasks_content, (
        "Collection 'ns' not exported in tasks.py"
    )

    # Verify __init__.py imports the collection
    init_file = pkg_dir / "src" / collection_slug / "__init__.py"
    assert init_file.exists(), "__init__.py not found"
    init_content = init_file.read_text()
    assert "from .tasks import ns" in init_content, (
        "Collection not imported in __init__.py"
    )
    assert "__all__" in init_content, "__all__ not defined in __init__.py"


def test_shebang_insertion(
    ctx: ToolkitContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    tasks = tmp_path / "tasks.py"
    tasks.write_text("")
    x = TestingToolkitProgram()
    x.run(["", "-x", "create.x", "--file", "tasks.py"])
    text = tasks.read_text()
    first_line, *_ = text.split("\n", maxsplit=1)
    assert first_line == "#!/usr/bin/env -S uv run --script"
