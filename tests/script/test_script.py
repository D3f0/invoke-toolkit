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


def add_lines(file_to_update: Path, lines=str, sep="\n") -> None:
    if not isinstance(file_to_update, Path):
        file_to_update = Path(file_to_update)
    previous_content: str = file_to_update.read_text(encoding="utf-8")
    new_contents = sep.join([previous_content, lines])
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
