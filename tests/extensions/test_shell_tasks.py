"""Tests for shell completion installation tasks."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from invoke_toolkit.extensions.tasks.shell import (
    Shell,
    _detect_shell,
    _get_bash_completion_dir,
    _get_fish_completion_dir,
    _get_zsh_completion_dir,
)


def test_shell_enum_values():
    """Test that Shell enum has expected values."""
    assert Shell.BASH.value == "bash"
    assert Shell.ZSH.value == "zsh"
    assert Shell.FISH.value == "fish"


def test_detect_shell_from_env_bash():
    """Test shell detection from SHELL environment variable for bash."""
    with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
        assert _detect_shell() == Shell.BASH


def test_detect_shell_from_env_zsh():
    """Test shell detection from SHELL environment variable for zsh."""
    with patch.dict(os.environ, {"SHELL": "/usr/bin/zsh"}):
        assert _detect_shell() == Shell.ZSH


def test_detect_shell_from_env_fish():
    """Test shell detection from SHELL environment variable for fish."""
    with patch.dict(os.environ, {"SHELL": "/usr/local/bin/fish"}):
        assert _detect_shell() == Shell.FISH


def test_detect_shell_unknown():
    """Test shell detection returns None for unknown shell."""
    with patch.dict(os.environ, {"SHELL": "/bin/tcsh"}):
        assert _detect_shell() is None


def test_detect_shell_no_env():
    """Test shell detection returns None when SHELL is not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove SHELL if it exists
        env = os.environ.copy()
        env.pop("SHELL", None)
        with patch.dict(os.environ, env, clear=True):
            assert _detect_shell() is None


def test_get_bash_completion_dir():
    """Test bash completion directory path."""
    expected = Path.home() / ".bashrc.d"
    assert _get_bash_completion_dir() == expected


def test_get_zsh_completion_dir():
    """Test zsh completion directory path."""
    expected = Path.home() / ".zfunc"
    assert _get_zsh_completion_dir() == expected


def test_get_fish_completion_dir():
    """Test fish completion directory path."""
    expected = Path.home() / ".config" / "fish" / "completions"
    assert _get_fish_completion_dir() == expected


def test_install_completions_requires_shell_when_not_detected():
    """Test that install_completions exits when shell cannot be detected."""
    from invoke_toolkit.extensions.tasks.shell import install_completions

    ctx = MagicMock()
    ctx.console = MagicMock()

    with patch.dict(os.environ, {}, clear=True):
        env = os.environ.copy()
        env.pop("SHELL", None)
        with patch.dict(os.environ, env, clear=True):
            # Call the underlying function, not the decorated task
            install_completions.body(ctx, shell=None)
            ctx.rich_exit.assert_called_once()
            assert "Could not detect shell" in str(ctx.rich_exit.call_args)


def test_completion_status_shows_all_shells():
    """Test that completion_status shows status for all shells."""
    from invoke_toolkit.extensions.tasks.shell import completion_status

    ctx = MagicMock()
    ctx.console = MagicMock()

    with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
        # Call the underlying function, not the decorated task
        completion_status.body(ctx)  # type: ignore[attr-defined]

    # Should have called print multiple times (header + 3 shells)
    assert ctx.console.print.call_count >= 4


def test_install_bash_completion_creates_file():
    """Test that bash completion installation creates the completion file."""
    from invoke_toolkit.extensions.tasks.shell import _install_bash_completion

    with tempfile.TemporaryDirectory() as tmpdir:
        bashrc_d = Path(tmpdir) / ".bashrc.d"

        ctx = MagicMock()
        ctx.console = MagicMock()
        ctx.run = MagicMock()
        ctx.run.return_value.failed = False
        ctx.run.return_value.stdout = "# bash completion script"

        with (
            patch(
                "invoke_toolkit.extensions.tasks.shell._get_bash_completion_dir",
                return_value=bashrc_d,
            ),
            patch(
                "invoke_toolkit.extensions.tasks.shell.Path.home",
                return_value=Path(tmpdir),
            ),
        ):
            result = _install_bash_completion(ctx, binary_name="intk")

        assert result == bashrc_d / "intk.bash"
        assert bashrc_d.exists()
        assert (bashrc_d / "intk.bash").exists()
        assert (bashrc_d / "intk.bash").read_text() == "# bash completion script"


def test_install_zsh_completion_creates_file():
    """Test that zsh completion installation creates the completion file."""
    from invoke_toolkit.extensions.tasks.shell import _install_zsh_completion

    with tempfile.TemporaryDirectory() as tmpdir:
        zfunc = Path(tmpdir) / ".zfunc"

        ctx = MagicMock()
        ctx.console = MagicMock()
        ctx.run = MagicMock()
        ctx.run.return_value.failed = False
        ctx.run.return_value.stdout = "# zsh completion script"

        with (
            patch(
                "invoke_toolkit.extensions.tasks.shell._get_zsh_completion_dir",
                return_value=zfunc,
            ),
            patch(
                "invoke_toolkit.extensions.tasks.shell.Path.home",
                return_value=Path(tmpdir),
            ),
        ):
            result = _install_zsh_completion(ctx, binary_name="intk")

        assert result == zfunc / "_intk"
        assert zfunc.exists()
        assert (zfunc / "_intk").exists()
        assert (zfunc / "_intk").read_text() == "# zsh completion script"


def test_install_fish_completion_creates_file():
    """Test that fish completion installation creates the completion file."""
    from invoke_toolkit.extensions.tasks.shell import _install_fish_completion

    with tempfile.TemporaryDirectory() as tmpdir:
        fish_completions = Path(tmpdir) / ".config" / "fish" / "completions"

        ctx = MagicMock()
        ctx.console = MagicMock()
        ctx.run = MagicMock()
        ctx.run.return_value.failed = False
        ctx.run.return_value.stdout = "# fish completion script"

        with patch(
            "invoke_toolkit.extensions.tasks.shell._get_fish_completion_dir",
            return_value=fish_completions,
        ):
            result = _install_fish_completion(ctx, binary_name="intk")

        assert result == fish_completions / "intk.fish"
        assert fish_completions.exists()
        assert (fish_completions / "intk.fish").exists()
        assert (
            fish_completions / "intk.fish"
        ).read_text() == "# fish completion script"


def test_uninstall_completions_removes_file():
    """Test that uninstall_completions removes the completion file."""
    from invoke_toolkit.extensions.tasks.shell import uninstall_completions

    with tempfile.TemporaryDirectory() as tmpdir:
        bashrc_d = Path(tmpdir) / ".bashrc.d"
        bashrc_d.mkdir(parents=True)
        completion_file = bashrc_d / "intk.bash"
        completion_file.write_text("# completion script")

        ctx = MagicMock()
        ctx.console = MagicMock()

        with patch(
            "invoke_toolkit.extensions.tasks.shell._get_bash_completion_dir",
            return_value=bashrc_d,
        ):
            # Call the underlying function, not the decorated task
            uninstall_completions.body(ctx, shell=Shell.BASH, binary_name="intk")

    assert not completion_file.exists()
    ctx.console.print.assert_called()


def test_uninstall_completions_handles_missing_file():
    """Test that uninstall_completions handles missing file gracefully."""
    from invoke_toolkit.extensions.tasks.shell import uninstall_completions

    with tempfile.TemporaryDirectory() as tmpdir:
        bashrc_d = Path(tmpdir) / ".bashrc.d"
        # Don't create the file

        ctx = MagicMock()
        ctx.console = MagicMock()

        with patch(
            "invoke_toolkit.extensions.tasks.shell._get_bash_completion_dir",
            return_value=bashrc_d,
        ):
            # Call the underlying function, not the decorated task
            uninstall_completions.body(ctx, shell=Shell.BASH, binary_name="intk")

    # Should print a message about file not found
    assert any("not found" in str(call) for call in ctx.console.print.call_args_list)


def test_ensure_bashrc_sources_bashrc_d_creates_bashrc():
    """Test that _ensure_bashrc_sources_bashrc_d creates .bashrc if missing."""
    from invoke_toolkit.extensions.tasks.shell import _ensure_bashrc_sources_bashrc_d

    with tempfile.TemporaryDirectory() as tmpdir:
        bashrc = Path(tmpdir) / ".bashrc"
        bashrc_d = Path(tmpdir) / ".bashrc.d"

        ctx = MagicMock()
        ctx.console = MagicMock()

        with (
            patch(
                "invoke_toolkit.extensions.tasks.shell.Path.home",
                return_value=Path(tmpdir),
            ),
            patch(
                "invoke_toolkit.extensions.tasks.shell._get_bash_completion_dir",
                return_value=bashrc_d,
            ),
        ):
            result = _ensure_bashrc_sources_bashrc_d(ctx)

        assert result is True
        assert bashrc.exists()
        assert ".bashrc.d" in bashrc.read_text()


def test_ensure_bashrc_sources_bashrc_d_skips_if_configured():
    """Test that _ensure_bashrc_sources_bashrc_d skips if already configured."""
    from invoke_toolkit.extensions.tasks.shell import _ensure_bashrc_sources_bashrc_d

    with tempfile.TemporaryDirectory() as tmpdir:
        bashrc = Path(tmpdir) / ".bashrc"
        bashrc_d = Path(tmpdir) / ".bashrc.d"
        bashrc.write_text("# existing config\nif [ -d ~/.bashrc.d ]; then\nfi\n")

        ctx = MagicMock()
        ctx.console = MagicMock()

        with (
            patch(
                "invoke_toolkit.extensions.tasks.shell.Path.home",
                return_value=Path(tmpdir),
            ),
            patch(
                "invoke_toolkit.extensions.tasks.shell._get_bash_completion_dir",
                return_value=bashrc_d,
            ),
        ):
            result = _ensure_bashrc_sources_bashrc_d(ctx)

        assert result is False


def test_ensure_zshrc_sources_zfunc_creates_zshrc():
    """Test that _ensure_zshrc_sources_zfunc creates .zshrc if missing."""
    from invoke_toolkit.extensions.tasks.shell import _ensure_zshrc_sources_zfunc

    with tempfile.TemporaryDirectory() as tmpdir:
        zshrc = Path(tmpdir) / ".zshrc"
        zfunc = Path(tmpdir) / ".zfunc"

        ctx = MagicMock()
        ctx.console = MagicMock()

        with (
            patch(
                "invoke_toolkit.extensions.tasks.shell.Path.home",
                return_value=Path(tmpdir),
            ),
            patch(
                "invoke_toolkit.extensions.tasks.shell._get_zsh_completion_dir",
                return_value=zfunc,
            ),
        ):
            result = _ensure_zshrc_sources_zfunc(ctx)

        assert result is True
        assert zshrc.exists()
        assert ".zfunc" in zshrc.read_text()
        assert "compinit" in zshrc.read_text()
