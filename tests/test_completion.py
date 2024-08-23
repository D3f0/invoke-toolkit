import shlex
import unittest.mock
from shutil import which

import pexpect
import pytest
from invoke.context import Context
from invoke_toolkit.main import program
from rich.console import Console


@pytest.mark.parametrize(
    "inv_script",
    [
        "inv",
        # We don't pass the binary yet
        # "invtk"
    ],
)
def test_completion_bashrc(
    inv_script,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    ctx: Context,
    tmp_home,
    tmp_path_in_PATH,
    task_py_in_tmp_path,
    child_timeout: int,
) -> None:
    """
    Test completion for bash
    """
    init_script = f"{tmp_path}/.bashrc"
    ctx.run(f"{inv_script} --print-completion-script bash > {init_script}")
    command, *args = shlex.split("bash -l")
    # Create a tasks.py with a function called one_task, that should be
    # presented as one-task
    task_py_in_tmp_path.add_task("one_task")

    child = pexpect.spawn(command, args=args, timeout=child_timeout, cwd=str(tmp_path))
    child.sendline(f"source {init_script}")
    child.expect("$")

    child.expect("$")
    # Make sure the complete flag is working
    child.sendline(f"{inv_script} --complete")
    child.expect("$")
    assert "one-task" in ctx.run("inv --complete", hide=True).stdout
    child.send(f"{inv_script} \t")
    try:
        child.expect("one-task")
    except pexpect.exceptions.TIMEOUT:
        raise AssertionError(f"{inv_script} {child.buffer.decode()}")


def test_completion_zshrc(
    ctx: Context,
    tmp_path,
    task_py_in_tmp_path,
    tmp_home,
    tmp_path_in_PATH,
    child_timeout: int,
) -> None:
    """
    Test completion for zsh
    """
    if not which("zsh"):
        raise pytest.skip("zsh not available")
    shell_init = f"{tmp_path}/.zshrc"
    ctx.run(f"invtk --print-completion-script zsh > {shell_init}")
    task_py_in_tmp_path.add_task("one_task")
    command, *args = shlex.split("zsh -l")
    child = pexpect.spawn(command, args=args, timeout=child_timeout, cwd=str(tmp_path))
    child.sendline(f"source {shell_init}")
    child.expect("$")
    child.sendline("inv --complete")
    child.expect("$")
    assert "one-task" in ctx.run("inv --complete", hide=True).stdout
    child.send("inv \t")
    try:
        child.expect("one-task")
    except pexpect.exceptions.TIMEOUT:
        raise AssertionError(child.buffer.decode())


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_completion_install(
    shell: str,
    ctx: Context,
    task_py_in_tmp_path,  # type: ignore
    tmp_home: None,
    tmp_path_in_PATH: None,
    monkeypatch: pytest.MonkeyPatch,
    child_timeout,
    # program_no_stdin: None,
):
    if not which(shell):
        raise pytest.skip(reason=f"{shell} not found.")
    monkeypatch.setenv("SHELL", which(shell))
    with unittest.mock.patch("invoke_toolkit.output.console", spec=Console) as mock_output:
        # No STDIN
        
        task_py_in_tmp_path.add_task("my_task", body='print("hello world")')
        ctx.run("invtk --complete", hide=True).stdout
        child = pexpect.spawn(f"{shell} -l", cwd=tmp_home, timeout=child_timeout)
        child.sendline(f"source ~/.{shell}rc")
        child.expect("$")
        available_collections = program.collection.collections
        a_collection = list(available_collections.keys())[0]
        complete_trigger, expected = a_collection[:3], a_collection[3:]
        child.send(f"invtk {complete_trigger}\t")
        try:
            child.expect(expected)
        except pexpect.exceptions.TIMEOUT:
            raise AssertionError(child.buffer)
