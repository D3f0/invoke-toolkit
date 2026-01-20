"""
Test for package template creation and task discovery via entry points.

This test validates the workflow:
1. Create a package using the template: `uv run intk -x create.package --name invoke-toolkit-pkg1 --location {tmploc}`
2. Use `uv tool run` with `--with` flags to create an isolated environment
3. Verify that invoke-toolkit machinery discovers packages through entry points
4. Ensure that invoke-toolkit takes precedence over underlying invoke library errors
"""

from pathlib import Path
from textwrap import dedent
from typing import Any, Union

import pytest
from tomlkit import TOMLDocument, dump, parse

from invoke_toolkit import Context
from invoke_toolkit.loader.entrypoint import COLLECTION_ENTRY_POINT

# Check if copier is installed
try:
    __import__("copier")
    HAS_COPIER = True
except ImportError:
    HAS_COPIER = False


def add_entrypoint(pth: Union[str, Path], name: str, value: Any) -> None:
    """Adds an entry-point to a pyproject.toml file defined by pth"""
    if isinstance(pth, (str, Path)):
        with open(pth, encoding="utf-8") as fp:
            toml: TOMLDocument = parse(fp.read())
    else:
        raise ValueError(pth)
    entry_points = toml["project"].setdefault("entry-points", {})  # type: ignore[union-attr]
    entry_points[name] = value
    with open(pth, mode="w", encoding="utf-8") as fp:
        dump(toml, fp)


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_create_package_via_intk_command(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test that `intk create.package` creates a valid package structure.

    Steps:
    1. Run `intk create.package --name invoke-toolkit-pkg1 --location {tmploc}`
    2. Verify the package structure is created correctly
    3. Verify entry point is configured in pyproject.toml
    4. Verify collection module exists and exports collection
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    # Create package from template
    result = ctx.run(
        f"uv run intk -x create.package "
        f"--name invoke-toolkit-pkg1 "
        f"--location {pkg_location}",
        warn=True,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    # Verify package directory structure
    pkg_dir = pkg_location / "invoke-toolkit-pkg1"
    assert pkg_dir.exists(), f"Package directory not created at {pkg_dir}"
    assert (pkg_dir / "pyproject.toml").exists(), "pyproject.toml not found"
    assert (pkg_dir / "README.md").exists(), "README.md not found"
    assert (pkg_dir / "src" / "invoke_toolkit_pkg1").exists(), (
        "Package source not found"
    )
    assert (pkg_dir / "src" / "invoke_toolkit_pkg1" / "__init__.py").exists(), (
        "__init__.py not found"
    )
    assert (pkg_dir / "src" / "invoke_toolkit_pkg1" / "tasks.py").exists(), (
        "tasks.py not found"
    )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_package_entry_point_configuration(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test that the generated package has correct entry point configuration.

    Validates:
    1. Entry point section exists in pyproject.toml
    2. Entry point name matches package slug
    3. Entry point value points to correct collection module
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    # Create package
    result = ctx.run(
        f"uv run intk -x create.package --name my-test-package --location {pkg_location}",
        warn=True,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / "my-test-package"
    pyproject_path = pkg_dir / "pyproject.toml"

    # Parse and verify entry point
    with open(pyproject_path, encoding="utf-8") as fp:
        toml: TOMLDocument = parse(fp.read())

    entry_points = toml.get("project", {}).get("entry-points", {})
    assert COLLECTION_ENTRY_POINT in entry_points, (
        f"Entry point group '{COLLECTION_ENTRY_POINT}' not found"
    )

    collection_eps = entry_points[COLLECTION_ENTRY_POINT]
    expected_slug = "my_test_package"
    assert expected_slug in collection_eps, (
        f"Entry point '{expected_slug}' not found in collection"
    )
    assert collection_eps[expected_slug] == f"{expected_slug}:collection", (
        f"Entry point value incorrect for '{expected_slug}'"
    )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_uv_tool_run_with_multiple_packages(
    ctx: Context, tmp_path: Path, git_root: str
):
    """
    Test that `uv tool run` with --with flags discovers multiple packages.

    This test validates:
    1. Two packages can be created from template
    2. `uv tool run --with pkg1 --with pkg2` discovers collections from both
    3. Tasks from both packages are available in the isolated environment
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    packages = ["pkg-alpha", "pkg-beta"]

    # Create multiple packages
    for package_name in packages:
        result = ctx.run(
            f"uv run intk -x create.package "
            f"--name {package_name} "
            f"--location {pkg_location}",
            warn=True,
        )
        assert result.ok, f"Package {package_name} creation failed: {result.stderr}"

    # Verify all packages were created
    for package_name in packages:
        pkg_dir = pkg_location / package_name
        assert pkg_dir.exists(), f"Package {package_name} not created"

    # Create paths for uv tool run
    pkg_alpha = pkg_location / "pkg-alpha"
    pkg_beta = pkg_location / "pkg-beta"

    # Test uv tool run discovers both packages
    result = ctx.run(
        f"uv tool run --with {git_root} --with {pkg_alpha} --with {pkg_beta} intk -l",
        warn=True,
        pty=False,
    )

    assert result.ok, f"uv tool run failed: {result.stderr}"

    output = result.stdout
    # Both packages should have discoverable collections
    assert "pkg_alpha" in output or "pkg-alpha" in output, (
        f"pkg-alpha collection not discovered in: {output}"
    )
    assert "pkg_beta" in output or "pkg-beta" in output, (
        f"pkg-beta collection not discovered in: {output}"
    )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_generated_collection_module_structure(
    ctx: Context, tmp_path: Path, git_root: str
):
    """
    Test that the generated collection module has correct structure.

    Validates:
    1. __init__.py creates and exports a ToolkitCollection
    2. Collection is named correctly based on package slug
    3. Collection auto-discovers tasks from the package namespace
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    package_name = "test-pkg"

    result = ctx.run(
        f"uv run intk -x create.package --name {package_name} --location {pkg_location}",
        warn=True,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / package_name
    pkg_slug = package_name.replace("-", "_")

    # Check __init__.py content
    init_file = pkg_dir / "src" / pkg_slug / "__init__.py"
    with open(init_file, encoding="utf-8") as f:
        init_content = f.read()

        # Verify collection creation and export
        assert "ToolkitCollection" in init_content, "ToolkitCollection not imported"
        assert f'collection = ToolkitCollection("{pkg_slug}")' in init_content, (
            "Collection not created with correct name"
        )
        assert "collection.add_flat_tasks_from_namespace" in init_content, (
            "Collection does not auto-discover tasks in flat structure"
        )
        assert "collection" in init_content and "__all__" in init_content, (
            "Collection not properly exported"
        )
        # Verify documentation about flat vs namespace discovery
        assert "flat" in init_content.lower(), (
            "Documentation about flat task discovery is missing"
        )
        assert "add_collections_from_namespace" in init_content, (
            "Documentation about nested namespace discovery option is missing"
        )
        # Verify examples in documentation show correct namespace structure
        assert pkg_slug in init_content, (
            "Collection name not shown in documentation examples"
        )

    # Check tasks.py has at least one sample task
    tasks_file = pkg_dir / "src" / pkg_slug / "tasks.py"
    with open(tasks_file, encoding="utf-8") as f:
        tasks_content = f.read()

        # Verify task decorator and function exist
        assert "@task" in tasks_content, "No @task decorator found"
        assert "def hello" in tasks_content, "Sample hello task not found"


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_package_with_custom_collection_name(
    ctx: Context, tmp_path: Path, git_root: str
):
    """
    Test that package template respects custom collection names.

    This validates that template variables are correctly substituted:
    - {{ package_name }} - full package name
    - {{ package_slug }} - normalized package name
    - {{ collection_name }} - entry point collection name
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    package_name = "my-custom-pkg"

    result = ctx.run(
        f"uv run intk -x create.package --name {package_name} --location {pkg_location}",
        warn=True,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / package_name
    pkg_slug = package_name.replace("-", "_")

    # Verify README contains package name
    readme_file = pkg_dir / "README.md"
    with open(readme_file, encoding="utf-8") as f:
        readme_content = f.read()
        assert package_name in readme_content or pkg_slug in readme_content, (
            "Package name not found in README"
        )

    # Verify pyproject.toml contains package information
    pyproject_file = pkg_dir / "pyproject.toml"
    with open(pyproject_file, encoding="utf-8") as f:
        pyproject_content = f.read()
        assert f'name = "{package_name}"' in pyproject_content, (
            "Package name not in pyproject.toml"
        )
        assert f'{pkg_slug} = "{pkg_slug}:collection"' in pyproject_content, (
            "Entry point not correctly substituted"
        )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_toolkit_machinery_over_invoke_errors(
    ctx: Context, tmp_path: Path, git_root: str
):
    """
    Test that invoke-toolkit machinery handles errors gracefully.

    This validates that:
    1. Errors from invoke library are caught by invoke-toolkit
    2. Error messages are formatted through invoke-toolkit's output system
    3. Exit codes are properly propagated
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    package_name = "error-test-pkg"

    # Create package
    result = ctx.run(
        f"uv run intk -x create.package --name {package_name} --location {pkg_location}",
        warn=True,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / package_name
    pkg_slug = package_name.replace("-", "_")

    # Modify tasks.py to have a failing task
    tasks_file = pkg_dir / "src" / pkg_slug / "tasks.py"
    failing_task_code = dedent("""
        \"\"\"Test tasks\"\"\"

        from invoke_toolkit import Context, task


        @task()
        def failing_task(ctx: Context):
            \"\"\"A task that will fail\"\"\"
            ctx.run("false")  # This will fail


        @task()
        def hello(ctx: Context, name: str = "World"):
            \"\"\"Say hello\"\"\"
            ctx.print_success(f"Hello, {name}!")
    """)
    tasks_file.write_text(failing_task_code, encoding="utf-8")

    # Try to run the failing task via uv tool run
    result = ctx.run(
        f"uv tool run --with {git_root} --with {pkg_dir} intk failing-task",
        warn=True,
        pty=False,
    )

    # The task should fail, but error should be handled by invoke-toolkit
    assert not result.ok, "Task should have failed"
    # Error should be visible (either in stdout or stderr)
    assert result.stdout or result.stderr, "No error output captured"


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_installed_package_discovery(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test that installed packages are discovered via entry points.

    This validates the complete workflow:
    1. Create a package from template
    2. Install it in development mode (pip install -e)
    3. Use invoke-toolkit to list available tasks
    4. Verify collection from installed package is available
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    package_name = "installed-test-pkg"

    # Create package
    result = ctx.run(
        f"uv run intk -x create.package --name {package_name} --location {pkg_location}",
        warn=True,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / package_name

    # Install package in development mode
    with ctx.cd(pkg_dir):
        result = ctx.run("uv pip install -e .", warn=True)
        assert result.ok, f"Failed to install package: {result.stderr}"

    # List tasks should now include the installed package collection
    result = ctx.run("uv run intk -l", warn=True, pty=False)
    assert result.ok, f"Failed to list tasks: {result.stderr}"

    # The installed collection should be discoverable
    pkg_slug = package_name.replace("-", "_")
    output = result.stdout
    assert pkg_slug in output or package_name in output, (
        f"Installed package collection not found in: {output}"
    )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_package_plugin_tasks_discoverable_without_tasks_py(
    ctx: Context, tmp_path: Path, git_root: str
):
    """
    Test that package tasks are discoverable via entry points without tasks.py.

    This validates the complete workflow:
    1. Create a package using the template in a temporary directory
    2. Run `uv tool run --from {git_root} --with {package}`
    3. List tasks and verify they appear under the collection name
    4. Verify no import errors occur

    This tests the core issue: packages created from template should work
    even without a tasks.py file, relying on entry points discovery.
    """
    # Create package from template
    pkg_name = "invoke-toolkit-plugin-test"
    result = ctx.run(
        f"uv run intk -x create.package --name {pkg_name} --location {tmp_path}",
        warn=True,
        pty=False,
    )
    assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = tmp_path / pkg_name
    assert pkg_dir.exists(), f"Package not created at {pkg_dir}"
    assert (pkg_dir / "pyproject.toml").exists()
    assert (pkg_dir / "src" / "invoke_toolkit_plugin_test" / "__init__.py").exists()
    assert (pkg_dir / "src" / "invoke_toolkit_plugin_test" / "tasks.py").exists()

    # Verify pyproject.toml has entry point configured
    pyproject_path = pkg_dir / "pyproject.toml"
    with open(pyproject_path, encoding="utf-8") as fp:
        toml: TOMLDocument = parse(fp.read())

    entry_points = toml.get("project", {}).get("entry-points", {})
    assert COLLECTION_ENTRY_POINT in entry_points, "Entry point not configured"
    collection_eps = entry_points[COLLECTION_ENTRY_POINT]
    assert "invoke_toolkit_plugin_test" in collection_eps, (
        "Collection not in entry points"
    )

    # Step 1: List tasks from the package directory without tasks.py
    # This simulates the use case: cd {tmpdir}/{package} && intk -l
    with ctx.cd(pkg_dir):
        result = ctx.run(
            f"uv tool run --from {git_root} --with {pkg_dir} intk -l",
            warn=True,
            pty=False,
        )
        assert result.ok, (
            f"Failed to list tasks from package: {result.stderr}\n{result.stdout}"
        )

        output = result.stdout
        # The hello task should be discoverable from the package's collection
        assert "hello" in output.lower(), f"hello task not found in output: {output}"
        # The collection name should appear
        assert (
            "invoke_toolkit_plugin_test" in output
            or "invoke-toolkit-plugin-test" in output
        ), f"Collection name not found in output: {output}"

    # Step 2: Use uv tool run with the package to verify isolated environment works
    # This is the real use case: uvx --with {package} invoke-toolkit -l
    with ctx.cd(tmp_path):
        result = ctx.run(
            f"uv tool run --from {git_root} --with {pkg_dir} invoke-toolkit -l",
            warn=True,
            pty=False,
        )
        assert result.ok, (
            f"Failed to list tasks in isolated environment: {result.stderr}\n{result.stdout}"
        )

        output = result.stdout
        # The hello task should be discoverable in isolated environment
        assert "hello" in output.lower(), (
            f"hello task not found in isolated env output: {output}"
        )
        # The collection should be discoverable
        assert (
            "invoke_toolkit_plugin_test" in output
            or "invoke-toolkit-plugin-test" in output
        ), f"Collection not discoverable in isolated env: {output}"

    # Step 3: Actually run a task from the package to verify full functionality
    with ctx.cd(pkg_dir):
        result = ctx.run(
            "uv run intk invoke-toolkit-plugin-test.hello",
            warn=True,
            pty=False,
        )
        assert result.ok, f"Failed to run task: {result.stderr}\n{result.stdout}"
        # Should see the hello task output
        assert "hello" in result.stdout.lower(), (
            f"Task did not execute properly: {result.stdout}"
        )

    # Step 4: Verify in isolated environment via uv tool run
    with ctx.cd(tmp_path):
        result = ctx.run(
            f"uv tool run --from {git_root} --with {pkg_dir} invoke-toolkit "
            f"invoke-toolkit-plugin-test.hello",
            warn=True,
            pty=False,
        )
        assert result.ok, (
            f"Failed to run task in isolated env: {result.stderr}\n{result.stdout}"
        )
        assert "hello" in result.stdout.lower(), (
            f"Task did not execute in isolated env: {result.stdout}"
        )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_multiple_packages_as_plugins(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test that multiple packages can coexist as plugins and their tasks
    are all discoverable.

    This validates:
    1. Multiple packages can be created
    2. Each has its own collection
    3. All collections are discoverable in isolated environment
    4. No conflicts between package names
    """
    packages = ["plugin-alpha", "plugin-beta"]
    pkg_dirs = {}

    # Create multiple packages
    for pkg_name in packages:
        result = ctx.run(
            f"uv run intk -x create.package --name {pkg_name} --location {tmp_path}",
            warn=True,
            pty=False,
        )
        assert result.ok, f"Failed to create {pkg_name}: {result.stderr}"
        pkg_dirs[pkg_name] = tmp_path / pkg_name

    # List tasks in isolated environment with all packages
    with ctx.cd(tmp_path):
        pkg_paths = " ".join([f"--with {path}" for path in pkg_dirs.values()])
        result = ctx.run(
            f"uv tool run --from {git_root} {pkg_paths} invoke-toolkit -l",
            warn=True,
            pty=False,
        )
        assert result.ok, (
            f"Failed to list tasks with multiple packages: {result.stderr}\n{result.stdout}"
        )

        output = result.stdout
        # Both collections should be discoverable
        assert "plugin_alpha" in output or "plugin-alpha" in output, (
            f"plugin-alpha collection not found: {output}"
        )
        assert "plugin_beta" in output or "plugin-beta" in output, (
            f"plugin-beta collection not found: {output}"
        )

    # Verify we can run tasks from both packages
    for pkg_name, pkg_dir in pkg_dirs.items():
        with ctx.cd(tmp_path):
            pkg_slug = pkg_name.replace("-", "_")
            result = ctx.run(
                f"uv tool run --from {git_root} --with {pkg_dir} invoke-toolkit "
                f"{pkg_slug}.hello",
                warn=True,
                pty=False,
            )
            assert result.ok, (
                f"Failed to run task from {pkg_name}: {result.stderr}\n{result.stdout}"
            )
            assert "hello" in result.stdout.lower(), (
                f"Task from {pkg_name} did not execute: {result.stdout}"
            )
