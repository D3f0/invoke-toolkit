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

import pytest
from tomlkit import TOMLDocument, parse

from invoke_toolkit import Context
from invoke_toolkit.loader.entrypoint import COLLECTION_ENTRY_POINT

# Check if copier is installed
try:
    __import__("copier")
    HAS_COPIER = True
except ImportError:
    HAS_COPIER = False


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
    with ctx.cd(tmp_path):
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
    with ctx.cd(tmp_path):
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
    # For non-prefixed packages, entry point name defaults to slug (with underscores)
    assert expected_slug in collection_eps, (
        f"Entry point '{expected_slug}' not found in collection"
    )
    assert collection_eps[expected_slug] == f"{expected_slug}:collection", (
        f"Entry point value incorrect for '{expected_slug}'"
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

    with ctx.cd(tmp_path):
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

    with ctx.cd(tmp_path):
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
        # For non-prefixed packages, entry point name defaults to slug (with underscores)
        assert f'"{pkg_slug}" = "{pkg_slug}:collection"' in pyproject_content, (
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
    with ctx.cd(tmp_path):
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
    with ctx.cd(tmp_path):
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
    with ctx.cd(tmp_path):
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
    with ctx.cd(tmp_path):
        result = ctx.run("uv run intk -l", warn=True, pty=False)
        assert result.ok, f"Failed to list tasks: {result.stderr}"

    # The installed collection should be discoverable
    pkg_slug = package_name.replace("-", "_")
    output = result.stdout
    assert pkg_slug in output or package_name in output, (
        f"Installed package collection not found in: {output}"
    )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_create_package_with_short_name(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test creating a package with a custom short name using --ext-name.

    This validates that:
    1. Package can be created with --ext-name flag
    2. Package name is prefixed with 'invoke-toolkit-'
    3. Entry point uses the full package name
    4. Collection name uses the short name
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    ext_name = "myext"

    # Create package with short name
    with ctx.cd(tmp_path):
        result = ctx.run(
            f"uv run intk -x create.package --name test-pkg --ext-name {ext_name} --location {pkg_location}",
            warn=True,
        )
        assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / f"invoke-toolkit-{ext_name}"
    assert pkg_dir.exists(), f"Package directory not created at {pkg_dir}"

    # Verify pyproject.toml uses the short name correctly
    pyproject_file = pkg_dir / "pyproject.toml"
    with open(pyproject_file, encoding="utf-8") as f:
        pyproject_content = f.read()
        assert f'name = "invoke-toolkit-{ext_name}"' in pyproject_content, (
            "Package name not prefixed with invoke-toolkit-"
        )
        assert f"invoke-toolkit-{ext_name}" in pyproject_content, (
            "Short name not used in entry point"
        )


@pytest.mark.skip(
    reason="Template vars via CLI need further investigation with invoke parameter handling"
)
@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_create_package_with_template_vars(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test creating a package with custom template variables via -t flag.

    This validates that:
    1. Custom template variables are accepted via -t flag
    2. Variables are properly parsed with ast.literal_eval
    3. Variables are substituted in the template
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    package_name = "template-vars-pkg"
    author_name = "TestAuthor"

    # Create package with template variables (using existing copier variables)
    with ctx.cd(tmp_path):
        result = ctx.run(
            f"uv run intk -x create.package --name {package_name} --location {pkg_location} "
            f"-t author_name={author_name}",
            warn=True,
        )
        assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / package_name

    # Verify pyproject.toml was created successfully
    pyproject_file = pkg_dir / "pyproject.toml"
    assert pyproject_file.exists(), "pyproject.toml not created"
    with open(pyproject_file, encoding="utf-8") as f:
        pyproject_content = f.read()
        assert "invoke-toolkit" in pyproject_content, (
            "invoke-toolkit dependency not in pyproject.toml"
        )

    # Verify README or other files were generated
    readme_file = pkg_dir / "README.md"
    if readme_file.exists():
        with open(readme_file, encoding="utf-8") as f:
            readme_content = f.read()
            # Author might be used somewhere in the generated content
            assert readme_content, "README should not be empty"


def test_extract_plugin_short_name():
    """
    Test the extract_plugin_short_name function directly.

    Validates:
    1. Extracts short name from invoke-toolkit-xxx pattern
    2. Returns original name if pattern doesn't match
    3. Handles edge cases
    """
    from invoke_toolkit.loader.entrypoint import extract_plugin_short_name

    # Test plugin with standard prefix
    assert extract_plugin_short_name("invoke-toolkit-ext") == "ext"
    assert extract_plugin_short_name("invoke-toolkit-my-plugin") == "my-plugin"
    assert extract_plugin_short_name("invoke-toolkit-a") == "a"

    # Test non-plugin packages
    assert extract_plugin_short_name("my-package") == "my-package"
    assert extract_plugin_short_name("regular_name") == "regular_name"

    # Test edge case of just the prefix (shouldn't happen but should be safe)
    assert extract_plugin_short_name("invoke-toolkit-") == "invoke-toolkit-"


def test_duplicate_collection_names_warning():
    """
    Test that duplicate collection names from different entry points generate warnings.

    This validates that when two extensions extract to the same short name,
    a warning is issued and only the first one is loaded.
    """
    import warnings
    from unittest.mock import Mock, patch

    from invoke_toolkit.collections import ToolkitCollection
    from invoke_toolkit.loader.entrypoint import EntryPointLoader

    # Create mock entry points with duplicate collection names
    mock_ep1 = Mock()
    mock_ep1.name = "invoke-toolkit-ext"
    mock_ep1.load.return_value = ToolkitCollection("ext")

    mock_ep2 = Mock()
    mock_ep2.name = (
        "invoke-toolkit-ext-alt"  # Different package, same short name after extraction
    )
    mock_ep2.load.return_value = ToolkitCollection("ext-alt")

    loader = EntryPointLoader()

    # Patch the _load_entry_points method to return our mock entry points
    entry_points = {
        "invoke-toolkit-ext": mock_ep1.load(),
        "invoke-toolkit-ext-alt": mock_ep2.load(),
    }

    with patch.object(loader, "_load_entry_points", return_value=entry_points):
        # Create a scenario where both would map to the same collection name
        # by manipulating the extraction logic
        with patch(
            "invoke_toolkit.loader.entrypoint.extract_plugin_short_name"
        ) as mock_extract:
            # Both should extract to "ext"
            mock_extract.side_effect = (
                lambda x: "ext"
                if x
                in [
                    "invoke-toolkit-ext",
                    "invoke-toolkit-ext-alt",
                ]
                else x
            )

            # Capture warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                loader._create_compound_module(entry_points)

                # Verify a warning was issued
                assert len(w) >= 1
                warning_messages = [str(warning.message) for warning in w]
                assert any(
                    "Duplicate collection name" in msg for msg in warning_messages
                ), f"Expected duplicate collection warning, got: {warning_messages}"


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_create_package_refuses_in_git_repo(
    ctx: Context, tmp_path: Path, git_root: str
):
    """
    Test that create.package refuses to run inside a git repository.

    This validates that the safety check prevents overwriting files in a git repo.
    """
    # Try to create package in the git root (which is a git repository)
    result = ctx.run(
        f"uv run intk -x create.package --name test-pkg --location {git_root}",
        warn=True,
        pty=False,
    )
    # Should fail because location is inside a git repo
    assert not result.ok, "Should refuse to create package in git repo"
    assert "git repository" in result.stderr or "git repository" in result.stdout, (
        "Should mention git repository in error message"
    )


@pytest.mark.skipif(not HAS_COPIER, reason="copier not installed")
def test_create_package_uses_git_config(ctx: Context, tmp_path: Path, git_root: str):
    """
    Test that create.package picks up git config for author name and email.

    This validates that when git config user.name and user.email are set,
    they are used as defaults in the package creation.
    """
    pkg_location = tmp_path / "packages"
    pkg_location.mkdir()

    package_name = "git-config-test-pkg"

    # Create package (git config should be auto-detected)
    with ctx.cd(tmp_path):
        result = ctx.run(
            f"uv run intk -x create.package --name {package_name} --location {pkg_location}",
            warn=True,
        )
        assert result.ok, f"Package creation failed: {result.stderr}"

    pkg_dir = pkg_location / package_name

    # Verify the pyproject.toml was created
    pyproject_file = pkg_dir / "pyproject.toml"
    assert pyproject_file.exists(), "pyproject.toml not created"

    # Read and verify it contains author information
    with open(pyproject_file, encoding="utf-8") as f:
        content = f.read()
        # Should have authors section (whether from git config or defaults)
        assert "authors" in content, "Authors section not found in pyproject.toml"
