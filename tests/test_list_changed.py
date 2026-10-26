"""Changed-task listing against real Git repositories and script processes."""

import json
import os
import re
import subprocess
import sys

import pexpect
import pytest


SCRIPT = '''# /// script
# dependencies = ["invoke-toolkit"]
# ///
from invoke_toolkit import task, script

@task(aliases=["u"], default=True)
def updated(ctx, value=1):
    """Original documentation."""
    return value

@task()
def stable(ctx):
    return 2

if __name__ == "__main__":
    script()
'''
NEW_TASK = """
@task(name="brand-new", aliases=["n"])
async def added(ctx):
    return 3
"""


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True
    )


@pytest.fixture
def task_repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.com")
    folder = tmp_path / "nested folder"
    folder.mkdir()
    path = folder / "tasks.py"
    path.write_text(SCRIPT)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "Baseline")
    return path


def run_script(path, *args, cwd=None):
    return subprocess.run(
        [sys.executable, str(path), *args],
        cwd=cwd or path.parent,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )


def listed_tasks(result):
    assert result.returncode == 0, result.stderr
    return {row["name"]: row for row in json.loads(result.stdout)["tasks"]}


def test_staged_and_unstaged_changes_preserve_aliases(task_repo, tmp_path):
    task_repo.write_text(SCRIPT.replace("return value", "return value + 1"))
    git(tmp_path, "add", ".")
    task_repo.write_text(
        task_repo.read_text().replace(
            'if __name__ == "__main__":', NEW_TASK + '\nif __name__ == "__main__":'
        )
    )
    tasks = listed_tasks(
        run_script(task_repo, "--list-changed", "--list-format", "json")
    )
    assert set(tasks) == {"updated", "brand-new"}
    assert tasks["updated"]["aliases"] == ["u"]
    assert tasks["brand-new"]["aliases"] == ["n"]


@pytest.mark.parametrize(
    "change",
    [
        ("value=1", "value=5"),
        ('aliases=["u"]', 'aliases=["another"]'),
        ("Original documentation.", "Revised documentation."),
        ("return value", "pass"),
    ],
)
def test_definition_changes_are_updated(task_repo, change):
    task_repo.write_text(SCRIPT.replace(*change))
    assert set(
        listed_tasks(run_script(task_repo, "--list-changed", "--list-format", "json"))
    ) == {"updated"}


def test_formatting_and_unrelated_edits_are_not_changes(task_repo):
    task_repo.write_text(
        SCRIPT.replace("return value", "return (value)  # comment") + "\nHELPER = 42\n"
    )
    result = run_script(task_repo, "--list-changed", "--list-format", "json")
    assert listed_tasks(result) == {}


@pytest.mark.parametrize("stage", [False, True])
def test_new_script_in_repository_lists_all_tasks(task_repo, stage):
    new_path = task_repo.parent / "new_tasks.py"
    new_path.write_text(SCRIPT)
    if stage:
        git(task_repo.parent, "add", str(new_path))
    assert set(
        listed_tasks(run_script(new_path, "--list-changed", "--list-format", "json"))
    ) == {"stable", "updated"}


def test_missing_git_does_not_break_normal_listing(tmp_path):
    path = tmp_path / "tasks.py"
    path.write_text(SCRIPT)
    assert set(listed_tasks(run_script(path, "--list", "--list-format", "json"))) == {
        "stable",
        "updated",
    }
    assert run_script(path, "--list-changed").returncode != 0


@pytest.mark.skipif(os.name == "nt", reason="PTYs are POSIX-only")
@pytest.mark.parametrize("list_format", ["flat", "nested"])
def test_normal_listing_highlights_changes_in_real_terminal(task_repo, list_format):
    task_repo.write_text(
        SCRIPT.replace("return value", "return value + 1").replace(
            'if __name__ == "__main__":', NEW_TASK + '\nif __name__ == "__main__":'
        )
    )
    env = dict(os.environ)
    env.pop("NO_COLOR", None)
    env["TERM"] = "xterm-256color"
    child = pexpect.spawn(
        sys.executable,
        [str(task_repo), "--list", "--list-format", list_format],
        cwd=str(task_repo.parent),
        env=env,
        encoding="utf-8",
        timeout=10,
    )
    try:
        child.expect(pexpect.EOF)
        output = str(child.before)
    finally:
        child.close(force=True)
    assert child.exitstatus == 0, output
    assert re.search(r"\x1b\[[0-9;]*32m[^\x1b]*brand-new", output)
    assert re.search(r"\x1b\[[0-9;]*33m[^\x1b]*updated", output)
    assert "stable" in output


def test_repository_without_commits_lists_tasks_as_new(tmp_path):
    git(tmp_path, "init", "-q")
    path = tmp_path / "tasks.py"
    path.write_text(SCRIPT)
    assert set(
        listed_tasks(run_script(path, "--list-changed", "--list-format", "json"))
    ) == {"stable", "updated"}


def test_history_is_parsed_without_executing_it(task_repo):
    task_repo.write_text(
        SCRIPT + '\nraise RuntimeError("historical code must not run")\n'
    )
    git(task_repo.parent, "add", ".")
    git(task_repo.parent, "commit", "-qm", "Old side effect")
    task_repo.write_text(SCRIPT.replace("return value", "return value + 1"))
    assert set(
        listed_tasks(run_script(task_repo, "--list-changed", "--list-format", "json"))
    ) == {"updated"}


@pytest.mark.parametrize("scope", [[], ["--list", "tools"], ["--list-tasks"]])
def test_loaded_collection_keeps_namespaces_and_excludes_imports(task_repo, scope):
    source = SCRIPT.replace(
        "from invoke_toolkit import task, script",
        "from invoke_toolkit import task, script, Collection",
    ).replace(
        'if __name__ == "__main__":',
        'ns = Collection()\nns.add_collection(Collection("tools", updated, stable))\n\nif __name__ == "__main__":',
    )
    task_repo.write_text(source)
    git(task_repo.parent, "add", ".")
    git(task_repo.parent, "commit", "-qm", "Namespace baseline")
    task_repo.write_text(source.replace("return value", "return value + 1"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "invoke_toolkit",
            "--list-changed",
            *scope,
            "--list-format",
            "json",
        ],
        cwd=task_repo.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    if scope == ["--list", "tools"]:
        assert {t["name"] for t in data["tasks"]} == {"updated"}
    else:
        assert data["tasks"] == []
        assert [c["name"] for c in data["collections"]] == ["tools"]
        assert {t["name"] for t in data["collections"][0]["tasks"]} == {"updated"}


def test_imported_tasks_are_not_classified_as_new(task_repo):
    (task_repo.parent / "external.py").write_text(
        "from invoke_toolkit import task\n@task()\ndef imported(ctx):\n    return 9\n"
    )
    task_repo.write_text(
        SCRIPT.replace("return value", "return value + 1").replace(
            'if __name__ == "__main__":',
            'from external import imported\n\nif __name__ == "__main__":',
        )
    )
    assert set(
        listed_tasks(run_script(task_repo, "--list-changed", "--list-format", "json"))
    ) == {"updated"}


def test_listing_resolves_repository_from_script_not_cwd(task_repo, tmp_path):
    task_repo.write_text(SCRIPT.replace("return value", "return value + 1"))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert set(
        listed_tasks(
            run_script(
                task_repo, "--list-changed", "--list-format", "json", cwd=elsewhere
            )
        )
    ) == {"updated"}


def test_filtering_preserves_explicit_default_overrides(task_repo):
    source = SCRIPT.replace(
        "from invoke_toolkit import task, script",
        "from invoke_toolkit import task, script, Collection",
    ).replace(
        'if __name__ == "__main__":',
        'ns = Collection()\nns.add_task(updated, name="first", default=False)\n'
        'ns.add_task(updated, name="second", default=False)\n\nif __name__ == "__main__":',
    )
    source = source.replace('aliases=["u"], default=True', "default=True")
    task_repo.write_text(source.replace("return value", "return value + 1"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "invoke_toolkit",
            "--list-changed",
            "--list-format",
            "json",
        ],
        cwd=task_repo.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    flat = subprocess.run(
        [sys.executable, "-m", "invoke_toolkit", "--list-changed"],
        cwd=task_repo.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert flat.returncode == 0, flat.stderr
    assert "first" in flat.stdout and "second" in flat.stdout
    assert json.loads(result.stdout)["default"] is None


@pytest.mark.parametrize("block", ["if True:", "try:"])
def test_module_control_flow_tasks_are_compared(task_repo, block):
    conditional = block + "\n    @task()\n    def conditional(ctx):\n        return 7\n"
    if block == "try:":
        conditional += "except Exception:\n    pass\n"
    source = SCRIPT.replace(
        'if __name__ == "__main__":', conditional + '\nif __name__ == "__main__":'
    )
    task_repo.write_text(source)
    git(task_repo.parent, "add", ".")
    git(task_repo.parent, "commit", "-qm", "Conditional task")
    task_repo.write_text(source.replace("return 7", "return 8"))
    assert set(
        listed_tasks(run_script(task_repo, "--list-changed", "--list-format", "json"))
    ) == {"conditional"}


@pytest.mark.skipif(os.name == "nt", reason="PTYs are POSIX-only")
def test_helper_converted_to_task_is_highlighted_as_new(task_repo):
    task_repo.write_text(SCRIPT.replace("@task()\ndef stable", "def stable"))
    git(task_repo.parent, "add", ".")
    git(task_repo.parent, "commit", "-qm", "Helper baseline")
    task_repo.write_text(SCRIPT)
    env = dict(os.environ)
    env.pop("NO_COLOR", None)
    env["TERM"] = "xterm-256color"
    child = pexpect.spawn(
        sys.executable,
        [str(task_repo), "--list-changed"],
        cwd=str(task_repo.parent),
        env=env,
        encoding="utf-8",
        timeout=10,
    )
    try:
        child.expect(pexpect.EOF)
        output = child.before
        assert isinstance(output, str)
    finally:
        child.close(force=True)
    assert child.exitstatus == 0, output
    assert re.search(r"\x1b\[[0-9;]*32m[^\x1b]*stable", output)


def test_reused_program_does_not_compare_stale_source(task_repo, tmp_path):
    local_root = tmp_path / "local-only"
    local_root.mkdir()
    (local_root / "local_tasks.py").write_text(
        "from invoke_toolkit import task\n@task()\ndef local_task(ctx):\n    return 1\n"
    )
    code = (
        "from invoke_toolkit.program import ToolkitProgram\n"
        "p = ToolkitProgram()\n"
        f"p.run(['intk', '-r', {str(task_repo.parent)!r}, '--list'], exit=False)\n"
        f"p.run(['intk', '-r', {str(local_root)!r}, '--list-changed'])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=local_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_shadowed_historical_definition_does_not_hide_update(task_repo):
    source = SCRIPT.replace(
        'if __name__ == "__main__":',
        '@task()\ndef stable(ctx):\n    return 3\n\nif __name__ == "__main__":',
    )
    task_repo.write_text(source)
    git(task_repo.parent, "add", ".")
    git(task_repo.parent, "commit", "-qm", "Shadowed task")
    task_repo.write_text(source.replace("return 3", "return 2"))
    assert set(
        listed_tasks(run_script(task_repo, "--list-changed", "--list-format", "json"))
    ) == {"stable"}


@pytest.mark.parametrize("decoration", ["task(stable)", "task()(stable)"])
def test_helper_promoted_by_direct_task_call_is_listed(task_repo, decoration):
    source = SCRIPT.replace("@task()\ndef stable", "def stable")
    task_repo.write_text(source)
    git(task_repo.parent, "add", ".")
    git(task_repo.parent, "commit", "-qm", "Plain helper")
    task_repo.write_text(
        source.replace(
            'if __name__ == "__main__":',
            f'stable = {decoration}\n\nif __name__ == "__main__":',
        )
    )
    assert set(
        listed_tasks(run_script(task_repo, "--list-changed", "--list-format", "json"))
    ) == {"stable"}
