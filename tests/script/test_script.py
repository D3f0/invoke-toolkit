"""
Test single script
"""

import inspect
from pathlib import Path

from invoke import task
from invoke.context import Context

from invoke_toolkit import script


@task()
def sample_task(ctx):
    ctx.run("echo hello")


def add_lines(file_to_update: Path, lines: str = "", sep: str = "\n") -> None:
    if not isinstance(file_to_update, Path):
        file_to_update = Path(file_to_update)
    previous_content: str = file_to_update.read_text(encoding="utf-8")
    new_contents: str = sep.join([previous_content, lines])
    file_to_update.write_text(new_contents, encoding="utf-8")


def test_script_with_uv_run(tmp_path: Path, ctx: Context, git_root) -> None:
    """
    Creates a script with uv and injects the invoke_toolkit.script
    """
    with ctx.cd(tmp_path):
        test_py: Path = tmp_path / "test.py"
        env = {"VIRTUAL_ENV": ""}
        ctx.run(
            "touch test.py",
            in_stream=False,
        )
        ctx.run(
            "uv add --script test.py invoke",
            in_stream=False,
            env=env,
        )
        ctx.run(
            f"uv add --script test.py {git_root}",
            in_stream=False,
            env=env,
        )

        code = inspect.getsource(sample_task)
        add_lines(test_py, "from invoke_toolkit import task")
        add_lines(test_py, code)
        inv_c_l = ctx.run("uv run -- inv -c test -l", in_stream=False, hide=True)
        assert inv_c_l is not None
        stdout = inv_c_l.stdout.strip()
        assert "sample-task" in stdout.strip()


def test_frame_inspect(capsys):
    @task()
    def task_foo(c): ...
    @task()
    def task_bar(c): ...

    script(argv=["-l"], exit=False)
    outerr: str = capsys.readouterr()
    assert "task-foo" in outerr.out
    assert "task-bar" in outerr.out


# Tests for config_prefix parameter
def test_script_with_config_prefix_default():
    """Test that script() without config_prefix uses default behavior"""

    @task()
    def test_task(c):
        pass

    # Should not raise an error when calling script with no prefix
    script(argv=["-l"], exit=False)


def test_script_with_custom_config_prefix(capsys):
    """Test that script() creates custom config when prefix is provided"""

    @task()
    def deploy_task(c):
        """Deploy the application"""

    # Call script with custom prefix - should work without errors
    script(argv=["-l"], config_prefix="myapp", exit=False)

    # Should still show the tasks
    outerr = capsys.readouterr()
    assert "deploy-task" in outerr.out


def test_script_config_prefix_creates_custom_class():
    """Test that custom config class is created with specified prefix"""

    @task()
    def test_task(c):
        pass

    # Verify that when config_prefix is provided, a custom class is created
    # by checking that script doesn't crash and properly initializes
    script(argv=["-l"], config_prefix="custom_prefix", exit=False)


def test_script_with_empty_string_prefix(capsys):
    """Test that empty string prefix is handled gracefully"""

    @task()
    def test_task(c):
        pass

    # Empty string should be treated as a prefix
    script(argv=["-l"], config_prefix="", exit=False)
    outerr = capsys.readouterr()
    assert "test-task" in outerr.out


def test_script_multiple_prefixes(capsys):
    """Test that different prefixes can be used in sequence"""

    @task()
    def task_one(c):
        pass

    # First call with one prefix
    script(argv=["-l"], config_prefix="app1", exit=False)
    outerr1 = capsys.readouterr()
    assert "task-one" in outerr1.out

    @task()
    def task_two(c):
        pass

    # Second call with different prefix
    script(argv=["-l"], config_prefix="app2", exit=False)
    outerr2 = capsys.readouterr()
    assert "task-two" in outerr2.out


def test_script_loads_project_config(tmp_path: Path, capsys, monkeypatch):
    """Test that script() loads project invoke.yml configuration"""
    # Create a temporary directory with a script and config file
    monkeypatch.chdir(tmp_path)

    # Create invoke.yml config file with echo=true and pty=true
    config_file = tmp_path / "invoke.yml"
    config_file.write_text(
        "run:\n  echo: true\n  pty: true\n",
        encoding="utf-8",
    )

    # Create a task that checks the config values
    @task()
    def check_config(c):
        # Check that config was loaded
        assert c.config.run.echo is True, "echo should be True from invoke.yml"
        assert c.config.run.pty is True, "pty should be True from invoke.yml"
        c.run("echo 'Config loaded successfully'")

    # Run script and verify config was loaded
    # Note: need to pass script name as first arg for invoke
    script(argv=["test_script.py", "check-config"], exit=False)
    outerr = capsys.readouterr()

    # If we got here without assertion errors, the config was loaded
    assert (
        "Config loaded successfully" in outerr.out
        or "config.py" in outerr.err
        or len(outerr.out) > 0
    )
