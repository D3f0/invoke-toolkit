import json
import os
import pkgutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from invoke_toolkit import Context, task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.extensions import tasks as extensions_tasks
from invoke_toolkit.testing import TestingToolkitProgram


def get_extension_collection_names() -> set[str]:
    """Dynamically discover all extension collection names."""
    return {module.name for module in pkgutil.iter_modules(extensions_tasks.__path__)}


def _install_completion_plugin(path: Path) -> Path:
    """Create importable plugin metadata and return its import sentinel path."""
    sentinel = path / "plugin-imported"
    (path / "fixture_plugin.py").write_text(
        "from pathlib import Path\n"
        "from invoke_toolkit import Collection, task\n"
        f"Path({str(sentinel)!r}).touch()\n"
        "@task\n"
        "def marker(ctx):\n"
        "    pass\n"
        "collection = Collection(marker)\n",
        encoding="utf-8",
    )
    metadata = path / "fixture_plugin-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: fixture-plugin\nVersion: 1.0\n",
        encoding="utf-8",
    )
    (metadata / "entry_points.txt").write_text(
        "[invoke_toolkit.collection]\nfixture-plugin = fixture_plugin:collection\n",
        encoding="utf-8",
    )
    return sentinel


def _complete_from(path: Path, *, disable_plugins: bool) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(path), env.get("PYTHONPATH", "")) if part
    )
    if disable_plugins:
        env["INVOKE_COMPLETION_DISABLE_PLUGINS"] = "1"
    else:
        env.pop("INVOKE_COMPLETION_DISABLE_PLUGINS", None)
    return subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--complete", "--", "intk"],
        cwd=path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@task()
def example_task_1(ctx: Context):
    ctx.run("echo example_task_1")


@task()
def example_task_2(ctx: Context):
    ctx.run("echo example_task_2")


def test_program_with_collection(capsys, suppress_stderr_logging):
    # verify that when the flag -x is passed, the extra collections are also listed
    coll = ToolkitCollection()
    coll.add_task(example_task_1)
    coll.add_task(example_task_2)

    p = TestingToolkitProgram(namespace=coll)
    p.run(["", "-xl", "--list-format", "json"])
    out, err = capsys.readouterr()
    assert not err, f"There should be no err output: {err}"
    task_list: dict[str, Any] = json.loads(out)
    collections = task_list.get("collections")
    assert collections, "collections not found in -x"
    expected_collections = get_extension_collection_names()
    actual_collections = set(c["name"] for c in collections)
    assert actual_collections.issubset(expected_collections), (
        f"Unexpected collections: {actual_collections - expected_collections}"
    )


def test_completion_with_x_flag(suppress_stderr_logging):
    """Test that completion includes internal collections when -x is passed"""
    result = subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--complete", "--", "intk", "-x"],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr

    # Check that internal collections are in the completion output
    assert "config" in output, "config collection should be in completion with -x"
    assert "create" in output, "create collection should be in completion with -x"


def test_completion_loads_entry_point_plugins_by_default(tmp_path):
    sentinel = _install_completion_plugin(tmp_path)

    result = _complete_from(tmp_path, disable_plugins=False)

    assert result.returncode == 0, result.stderr
    assert "fixture-plugin.marker" in result.stdout
    assert sentinel.exists()


def test_completion_can_skip_entry_point_plugins(tmp_path):
    sentinel = _install_completion_plugin(tmp_path)
    (tmp_path / "tasks.py").write_text(
        "from invoke_toolkit import Collection, task\n"
        "@task\n"
        "def project_marker(ctx):\n"
        "    pass\n"
        "ns = Collection(project_marker)\n",
        encoding="utf-8",
    )

    result = _complete_from(tmp_path, disable_plugins=True)

    assert result.returncode == 0, result.stderr
    assert "fixture-plugin.marker" not in result.stdout
    assert "project-marker" in result.stdout
    assert not sentinel.exists()


def test_completion_can_skip_entry_point_plugins_from_project_config(tmp_path):
    sentinel = _install_completion_plugin(tmp_path)
    (tmp_path / "tasks.py").write_text(
        "from invoke_toolkit import Collection, task\n"
        "@task\n"
        "def project_marker(ctx):\n"
        "    pass\n"
        "ns = Collection(project_marker)\n",
        encoding="utf-8",
    )
    (tmp_path / "invoke.yaml").write_text(
        "completion:\n  disable_plugins: true\n",
        encoding="utf-8",
    )

    result = _complete_from(tmp_path, disable_plugins=False)

    assert result.returncode == 0, result.stderr
    assert "fixture-plugin.marker" not in result.stdout
    assert "project-marker" in result.stdout
    assert not sentinel.exists()


def test_plugin_completion_opt_out_does_not_affect_execution(tmp_path):
    sentinel = _install_completion_plugin(tmp_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(tmp_path), env.get("PYTHONPATH", "")) if part
    )
    env["INVOKE_COMPLETION_DISABLE_PLUGINS"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--list"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "fixture-plugin.marker" in result.stdout
    assert sentinel.exists()


def test_plugin_completion_opt_out_keeps_internal_collections(tmp_path):
    env = os.environ.copy()
    env["INVOKE_COMPLETION_DISABLE_PLUGINS"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "invoke_toolkit",
            "--complete",
            "--",
            "intk",
            "-x",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "config" in result.stdout
    assert "create" in result.stdout


def test_internal_completion_does_not_import_copier():
    """Completing built-in task names must not load the optional Copier stack."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "from invoke_toolkit.testing import TestingToolkitProgram; "
                "TestingToolkitProgram().run("
                "['intk', '--complete', '--', 'intk', '-x'], exit=False); "
                "assert 'copier' not in sys.modules, "
                "'copier imported during completion'"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_completion_without_x_flag(suppress_stderr_logging):
    """Test that completion does not include internal collections without -x"""
    result = subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--complete", "--", "intk"],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    lines = output.strip().split("\n")

    # Count how many internal collection items appear
    internal_items = sum(
        1 for line in lines if "config." in line or "create." in line or "dist." in line
    )

    # There should be no internal collection items without -x
    assert internal_items == 0, (
        f"Found {internal_items} internal collection items without -x flag"
    )
