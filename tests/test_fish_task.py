from pathlib import Path
from unittest.mock import MagicMock

import tasks


def test_fish_builds_and_runs_fish_test_container(monkeypatch):
    ctx = MagicMock()
    repo_root = Path("/workspace/invoke-toolkit")
    monkeypatch.setattr(tasks, "REPO_ROOT", repo_root)

    tasks.fish.body(ctx)

    assert ctx.run.call_args_list[0].args[0] == (
        "docker build --file /workspace/invoke-toolkit/tests/Dockerfile.fish "
        "--tag invoke-toolkit-fish-test --load /workspace/invoke-toolkit"
    )
    assert ctx.run.call_args_list[1].args[0] == (
        "docker run --rm --interactive --tty "
        "--volume /workspace/invoke-toolkit:/workspace "
        "--workdir /workspace invoke-toolkit-fish-test --interactive"
    )
    assert all(call.kwargs.get("pty") is True for call in ctx.run.call_args_list)


def test_fish_quotes_paths(monkeypatch):
    ctx = MagicMock()
    monkeypatch.setattr(tasks, "REPO_ROOT", Path("/workspace/repo with spaces"))

    tasks.fish.body(ctx)

    assert (
        "'/workspace/repo with spaces/tests/Dockerfile.fish'"
        in (ctx.run.call_args_list[0].args[0])
    )
    assert (
        "'/workspace/repo with spaces:/workspace'"
        in (ctx.run.call_args_list[1].args[0])
    )

    config = Path("tests/fish.config.fish").read_text(encoding="utf-8")

    assert "intk -x shell.ic --shell fish" in config
    assert "source ~/.config/fish/completions/intk.fish" in config
