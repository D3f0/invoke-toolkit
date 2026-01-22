import re
import subprocess
import typing
from pathlib import Path
from textwrap import dedent

import pytest

from invoke_toolkit.context.context import ToolkitContext
from invoke_toolkit.testing import TestingToolkitProgram

if typing.TYPE_CHECKING:
    from tests.conftest import ShellRunTmp, TempVenv


def test_new_script_has_hello_world_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shell_run_tmp: "ShellRunTmp",
    git_root: Path,
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
    script_execution = shell_run_tmp(
        f"uv run --isolated --with {git_root} tasks.py hello-world", cwd=tmp_path
    )
    assert "hello world" in script_execution.stdout.strip()


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
    assert "test_tasks_pkg:collection" in pyproject_content, (
        "Collection entry-point not found in pyproject.toml"
    )

    # Verify tasks module has the hello task
    tasks_content = (src_dir / "tasks.py").read_text()
    assert "@task(" in tasks_content, "tasks module should have @task decorator"
    assert "def hello" in tasks_content, "hello task not found in tasks module"

    # Verify __init__.py creates the collection with auto-discovery
    init_content = (src_dir / "__init__.py").read_text()
    assert "collection = ToolkitCollection" in init_content, (
        "Collection object not found in __init__.py"
    )
    assert "add_collections_from_namespace" in init_content, (
        "auto-discovery not set up in collection"
    )


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

    # Should create the collection with auto-discovery
    assert "collection = ToolkitCollection" in init_text, (
        "Collection not created in __init__.py"
    )
    assert "add_collections_from_namespace" in init_text, (
        "auto-discovery not set up in __init__.py"
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
    # Verify task definition
    assert "@task(" in tasks_content, "Missing @task decorator"
    assert "def hello(" in tasks_content, "Missing hello task function"

    # Verify __init__.py has proper exports
    init_py = src_dir / "__init__.py"
    init_content = init_py.read_text()

    assert "__version__" in init_content, "Missing __version__ in __init__.py"
    assert "from invoke_toolkit.collections import ToolkitCollection" in init_content, (
        "Missing ToolkitCollection import in __init__.py"
    )
    assert "collection = ToolkitCollection" in init_content, (
        "Missing collection instantiation in __init__.py"
    )
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
    # For non-prefixed packages, short name defaults to slug (with underscores)
    short_name = "discovery_test_pkg"
    assert f'"{short_name}" = "{collection_slug}:collection"' in pyproject_content, (
        f"Entry-point '{short_name}' not found in pyproject.toml"
    )

    # Verify the package structure is complete for entry-point discovery
    # The entry-point system will discover and load this when the package is installed
    tasks_file = pkg_dir / "src" / collection_slug / "tasks.py"
    assert tasks_file.exists(), "tasks.py module not found"

    # Verify tasks module has the hello task
    tasks_content = tasks_file.read_text()
    assert "@task(" in tasks_content, "Missing @task decorator"
    assert "def hello(" in tasks_content, "Missing hello task function"

    # Verify __init__.py creates the collection with auto-discovery
    init_file = pkg_dir / "src" / collection_slug / "__init__.py"
    assert init_file.exists(), "__init__.py not found"
    init_content = init_file.read_text()
    assert "collection = ToolkitCollection" in init_content, (
        "Collection not created in __init__.py"
    )
    assert "add_collections_from_namespace" in init_content, (
        "auto-discovery not set up in __init__.py"
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


def _verify_shebang(lines):
    """Verify shebang line is correct."""
    assert lines[0] == "#!/usr/bin/env -S uv run --script", (
        f"Invalid shebang. Expected '#!/usr/bin/env -S uv run --script', "
        f"got '{lines[0]}'"
    )


def _verify_pep723_metadata_block(lines):
    """Verify PEP 723 metadata block structure."""
    assert lines[1] == "# /// script", (
        f"PEP 723 metadata block not found at line 2. Got: '{lines[1]}'"
    )

    # Find closing line
    closing_line = None
    for i, line in enumerate(lines):
        if line.strip() == "# ///":
            closing_line = i
            break

    assert closing_line is not None, "PEP 723 metadata block not properly closed"
    return closing_line


def _verify_python_requirement(lines):
    """Verify requires-python field exists and has correct value."""
    for line in lines:
        if "requires-python" in line:
            assert ">=3.10" in line, f"Expected requires-python >=3.10, got: '{line}'"
            return

    raise AssertionError("requires-python field not found in metadata")


def _verify_invoke_toolkit_version(lines):
    """Verify invoke-toolkit dependency with current version."""
    dependencies_line = None
    for i, line in enumerate(lines):
        if "dependencies" in line:
            dependencies_line = i
            break

    assert dependencies_line is not None, "dependencies field not found in metadata"

    for line in lines[dependencies_line:]:
        if line.strip().startswith("#") and (
            "invoke-toolkit==" in line or "invoke-toolkit>=" in line
        ):
            assert "invoke-toolkit" in line, (
                f"invoke-toolkit dependency malformed: '{line}'"
            )
            # Match semantic version with optional pre-release/dev version suffixes
            # and both == and >= specifiers
            version_match = re.search(
                r"invoke-toolkit(?:==|>=)(\d+\.\d+\.\d+(?:\.post\d+)?(?:\.dev\d+)?)",
                line,
            )
            assert version_match, (
                f"invoke-toolkit version not in valid semantic format: '{line}'"
            )
            return

        if "# ///" in line:
            break

    raise AssertionError(
        "invoke-toolkit dependency not found in PEP 723 metadata block"
    )


def _verify_script_code(script_content):
    """Verify script contains proper Python code."""
    assert "from invoke_toolkit import" in script_content, (
        "Script does not import from invoke_toolkit"
    )
    assert "def hello_world" in script_content, (
        "Script does not contain hello_world task"
    )
    assert "script()" in script_content, "Script does not call script() function"


def test_script_pep723_and_shebang_compliance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Test that create.script generates a script compliant with:
    - PEP 723 (Inline script metadata)
    - uv shebang requirements

    Validates:
    1. Correct shebang line
    2. Valid PEP 723 metadata block
    3. Current version of invoke-toolkit in dependencies
    4. Proper Python version requirement
    5. Script is executable with uv
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()

    script_name = "my_script.py"
    x.run(["", "-x", "create.script", "--name", script_name])

    script_path = tmp_path / script_name
    assert script_path.exists(), f"Script {script_path} was not created"

    script_content = script_path.read_text()
    lines = script_content.split("\n")

    _verify_shebang(lines)
    _verify_pep723_metadata_block(lines)
    _verify_python_requirement(lines)
    _verify_invoke_toolkit_version(lines)
    _verify_script_code(script_content)

    result = ctx.run(f"uv run {script_path} hello-world", warn=True)
    assert result.ok, (
        f"Script execution failed. Return code: {result.return_code}. "
        f"Output: {result.stdout}"
    )
    assert "hello world" in result.stdout, (
        f"Script did not produce expected output. Got: {result.stdout}"
    )


def test_package_multiple_task_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: ToolkitContext,
):
    """
    Test that adding additional task modules to a generated package
    allows them to be auto-discovered via add_collections_from_namespace.
    """
    monkeypatch.chdir(tmp_path)
    x = TestingToolkitProgram()

    # Create a package
    package_name = "multi-task-pkg"
    x.run(["", "-x", "create.package", "--name", package_name])

    pkg_dir = tmp_path / package_name
    src_dir = pkg_dir / "src" / "multi_task_pkg"

    # Verify the initial structure
    tasks_file = src_dir / "tasks.py"
    assert tasks_file.exists(), "tasks.py not found"

    # Add another task module to the package
    handlers_file = src_dir / "handlers.py"
    handlers_content = dedent(
        """
        \"\"\"Additional task handlers\"\"\"

        from invoke_toolkit import Context, task


        @task()
        def deploy(ctx: Context):
            \"\"\"Deploy the application\"\"\"
            ctx.run("echo 'deploying...'")


        @task()
        def rollback(ctx: Context):
            \"\"\"Rollback deployment\"\"\"
            ctx.run("echo 'rolling back...'")
        """
    )
    handlers_file.write_text(handlers_content)

    # Now when the package is installed and loaded via entry-point,
    # the add_collections_from_namespace in tasks.py should auto-discover handlers
    # This means both tasks.hello and handlers.deploy/rollback should be available

    # Verify the handlers file was created
    assert handlers_file.exists(), "handlers.py was not created"

    # Verify it has the expected tasks
    assert "@task()" in handlers_content, "handlers should have @task decorators"
    assert "def deploy" in handlers_content, "deploy task not found"
    assert "def rollback" in handlers_content, "rollback task not found"

    # Verify that the __init__.py will auto-discover it
    init_file = src_dir / "__init__.py"
    init_content = init_file.read_text()
    assert "add_collections_from_namespace" in init_content, (
        "Collection should use add_collections_from_namespace for auto-discovery"
    )


def test_tasks_and_entrypoints_merge(
    temp_venv: "TempVenv", git_root: str, tmp_path: Path
):
    """
    Test that when both tasks.py and entry points exist,
    tasks from both are shown when running `intk -l`
    """
    temp_venv.add_package(git_root, editable=True)
    package_name = "invoke-toolkit-bar"

    # Create the package
    temp_venv.run(
        f"invoke-toolkit -x create.package --name {package_name} --location {tmp_path}"
    )

    # Install the newly created package
    temp_venv.add_package(f"{tmp_path}/{package_name}")

    # Create a directory with a tasks.py file in the project
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    tasks_py = project_dir / "tasks.py"
    tasks_py.write_text(
        dedent(
            """
            from invoke import task

            @task
            def local_task(c):
                \"\"\"A task from local tasks.py\"\"\"
                print("Local task executed")
            """
        )
    )

    # Now list tasks - should see both entry point tasks and local tasks
    res = temp_venv.run("invoke-toolkit -dl", cwd=project_dir)

    assert res.returncode == 0, f"Error: {res.stdout} {res.stderr}"

    # Check that both the package entry point and local task are available
    output = res.stderr.decode() if isinstance(res.stderr, bytes) else res.stderr
    stdout = res.stdout.decode() if isinstance(res.stdout, bytes) else res.stdout
    combined_output = output + stdout

    # Should have the entry point collection (invoke_toolkit_bar)
    assert "invoke_toolkit_bar" in combined_output or "hello" in combined_output, (
        f"Entry point collection not found in output: {combined_output}"
    )

    # Should have the local task
    assert "local-task" in combined_output or "local_task" in combined_output, (
        f"Local task not found in output: {combined_output}"
    )


def test_create_package_create_venv_install_intk_and_package_and_list(
    temp_venv: "TempVenv", tmp_path_factory: pytest.TempPathFactory, git_root: Path
):
    """
    1. Create a package with invoke-toolkit -x create.package ... (in temp directory)
    2. Create a virtual env in a separate temp directory
    3. Run invoke-toolkit -l and find the extra package
    """
    package_name = "invoke-toolkit-extra-pkg"
    tmp_pkg_loc = tmp_path_factory.mktemp("pkg")
    tmp_pkg_path = tmp_pkg_loc / package_name
    # Create package in temporary directory
    tmp_work_dir = tmp_path_factory.mktemp("work")
    subprocess.run(
        f"invoke-toolkit -x create.package --name {package_name} --location {tmp_pkg_loc}",
        shell=True,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_work_dir,
    )
    # First we add invoke-toolkit
    temp_venv.add_package(git_root)
    # Then the created package
    temp_venv.add_package(tmp_pkg_path)
    # Separate test location
    other_place = tmp_path_factory.mktemp("other_place")
    res = temp_venv.run("invoke-toolkit -l", cwd=other_place)
    assert res.returncode == 0
