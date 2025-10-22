"""
Test single script
"""

from invoke import task
from invoke.context import Context
import inspect
from pathlib import Path
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
