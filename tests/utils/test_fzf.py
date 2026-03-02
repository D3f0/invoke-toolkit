"""Tests for fzf selector utilities."""

from unittest.mock import Mock, patch

import pytest

from invoke_toolkit import Context
from invoke_toolkit.utils.fzf import (
    _rich_select,
    _show_fzf_warning,
    is_fzf_available,
    select,
    select_from_command,
)

# Tests for is_fzf_available function


def test_is_fzf_available_returns_true_when_installed():
    """Test that function returns True when fzf is in PATH."""
    with patch("invoke_toolkit.utils.fzf.which", return_value="/usr/bin/fzf"):
        assert is_fzf_available() is True


def test_is_fzf_available_returns_false_when_not_installed():
    """Test that function returns False when fzf is not in PATH."""
    with patch("invoke_toolkit.utils.fzf.which", return_value=None):
        assert is_fzf_available() is False


# Tests for select function


def test_select_raises_error_when_fzf_not_available():
    """Test that RuntimeError is raised when fzf is not installed."""
    ctx = Context()
    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with pytest.raises(RuntimeError, match="fzf is not installed"):
            select(ctx, ["option1", "option2"], use_fallback=False)


def test_select_returns_none_when_choices_empty():
    """Test that None is returned when choices list is empty."""
    ctx = Context()
    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        result = select(ctx, [])
        assert result is None


def test_select_returns_empty_list_when_choices_empty_and_multi():
    """Test that empty list is returned when choices empty and multi=True."""
    ctx = Context()
    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        result = select(ctx, [], multi=True)
        assert result == []


def test_select_returns_selected_choice():
    """Test that selected choice is returned."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option2"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch("invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result):
            result = select(ctx, ["option1", "option2", "option3"])
            assert result == "option2"


def test_select_returns_none_when_user_cancels():
    """Test that None is returned when user cancels selection."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 1

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch("invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result):
            result = select(ctx, ["option1", "option2"])
            assert result is None


def test_select_returns_empty_list_when_user_cancels_multi():
    """Test that empty list is returned when user cancels with multi=True."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 1

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch("invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result):
            result = select(ctx, ["option1", "option2"], multi=True)
            assert result == []


def test_select_returns_multiple_selections_when_multi():
    """Test that multiple selections are returned when multi=True."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1\noption3"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch("invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result):
            result = select(
                ctx, ["option1", "option2", "option3", "option4"], multi=True
            )
            assert result == ["option1", "option3"]


def test_select_builds_correct_fzf_command_with_basic_options():
    """Test that fzf command is built correctly with basic options."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch(
            "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result
        ) as mock_run:
            select(
                ctx,
                ["option1", "option2"],
                prompt="Choose wisely",
                height="50%",
                reverse=False,
            )

            call_args = mock_run.call_args[0][0]
            assert '--prompt="Choose wisely: "' in call_args
            assert "--height=50%" in call_args
            assert "--reverse" not in call_args


def test_select_builds_correct_fzf_command_with_preview():
    """Test that fzf command includes preview options."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "file.txt"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch(
            "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result
        ) as mock_run:
            select(
                ctx,
                ["file.txt", "other.txt"],
                preview="cat {}",
                preview_window="right:60%",
            )

            call_args = mock_run.call_args[0][0]
            assert "--preview='cat {}'" in call_args
            assert "--preview-window=right:60%" in call_args


def test_select_includes_multi_flag_when_multi_true():
    """Test that --multi flag is included when multi=True."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch(
            "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result
        ) as mock_run:
            select(ctx, ["option1", "option2"], multi=True)

            call_args = mock_run.call_args[0][0]
            assert "--multi" in call_args


def test_select_includes_custom_kwargs_as_fzf_options():
    """Test that custom kwargs are converted to fzf options."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch(
            "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result
        ) as mock_run:
            select(ctx, ["option1", "option2"], ansi=True, border="rounded", exact=True)

            call_args = mock_run.call_args[0][0]
            assert "--ansi" in call_args
            assert "--border=rounded" in call_args
            assert "--exact" in call_args


# Tests for select_from_command function


def test_select_from_command_raises_error_when_fzf_not_available():
    """Test that RuntimeError is raised when fzf is not installed."""
    ctx = Context()
    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with pytest.raises(RuntimeError, match="fzf is not installed"):
            select_from_command(ctx, "ls", use_fallback=False)


def test_select_from_command_returns_selected_item():
    """Test that selected item from command output is returned."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "file1.txt\nfile2.txt\nfile3.txt"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 0
    mock_fzf_result.stdout = "file2.txt"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ):
                result = select_from_command(ctx, "ls *.txt", prompt="Select file")
                assert result == "file2.txt"


def test_select_from_command_returns_none_when_user_cancels():
    """Test that None is returned when user cancels selection."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "file1.txt\nfile2.txt"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 1

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ):
                result = select_from_command(ctx, "ls")
                assert result is None


def test_select_from_command_returns_multiple_items_when_multi():
    """Test that multiple items are returned when multi=True."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "branch1\nbranch2\nbranch3"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 0
    mock_fzf_result.stdout = "branch1\nbranch2"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ):
                result = select_from_command(ctx, "git branch", multi=True)
                assert result == ["branch1", "branch2"]


def test_select_from_command_pipes_command_to_fzf():
    """Test that command output is piped to fzf."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "result"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 0
    mock_fzf_result.stdout = "result"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result) as mock_run:
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ):
                select_from_command(ctx, "echo 'test'")

                # Verify the command was run
                mock_run.assert_called_once()
                assert "echo 'test'" in mock_run.call_args[0][0]


def test_select_from_command_includes_preview_options():
    """Test that preview options are included in command."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "container1\ncontainer2"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 0
    mock_fzf_result.stdout = "container1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ) as mock_fzf:
                select_from_command(
                    ctx,
                    "docker ps --format '{{.Names}}'",
                    preview="docker logs --tail 20 {}",
                )

                call_args = mock_fzf.call_args[0][0]
                assert "--preview='docker logs --tail 20 {}'" in call_args


# Tests for rich fallback selector


def test_select_uses_fallback_when_fzf_not_available():
    """Test that select uses rich fallback when fzf is not available."""
    ctx = Context()

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch(
            "invoke_toolkit.utils.fzf._rich_select", return_value="option2"
        ) as mock_rich:
            result = select(ctx, ["option1", "option2", "option3"], use_fallback=True)

            # Should call rich fallback
            mock_rich.assert_called_once()
            assert result == "option2"


def test_select_raises_error_when_fallback_disabled():
    """Test that select raises error when fzf unavailable and fallback disabled."""
    ctx = Context()

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with pytest.raises(RuntimeError, match="fzf is not installed"):
            select(ctx, ["option1", "option2"], use_fallback=False)


def test_select_from_command_uses_fallback_when_fzf_not_available():
    """Test that select_from_command uses rich fallback when fzf not available."""
    ctx = Context()
    mock_result = Mock()
    mock_result.ok = True
    mock_result.stdout = "file1.txt\nfile2.txt\nfile3.txt\n"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch.object(ctx, "run", return_value=mock_result):
            with patch(
                "invoke_toolkit.utils.fzf._rich_select", return_value="file2.txt"
            ) as mock_rich:
                result = select_from_command(ctx, "ls *.txt", use_fallback=True)

                # Should call rich fallback with parsed choices
                mock_rich.assert_called_once()
                call_args = mock_rich.call_args[0]
                assert call_args[0] == ["file1.txt", "file2.txt", "file3.txt"]
                assert result == "file2.txt"


def test_rich_select_returns_none_when_choices_empty():
    """Test that _rich_select returns None when choices are empty."""
    result = _rich_select([])
    assert result is None


def test_rich_select_returns_empty_list_when_choices_empty_and_multi():
    """Test that _rich_select returns empty list when choices empty and multi=True."""
    result = _rich_select([], multi=True)
    assert not result


def test_rich_select_returns_selected_choice():
    """Test that _rich_select returns selected choice."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="2"):
        result = _rich_select(["option1", "option2", "option3"])
        assert result == "option2"


def test_rich_select_returns_none_when_user_quits():
    """Test that _rich_select returns None when user enters 'q'."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="q"):
        result = _rich_select(["option1", "option2"])
        assert result is None


def test_rich_select_returns_empty_list_when_user_quits_multi():
    """Test that _rich_select returns empty list when user quits with multi=True."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="q"):
        result = _rich_select(["option1", "option2"], multi=True)
        assert not result


def test_rich_select_handles_invalid_number():
    """Test that _rich_select handles invalid number input."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="99"):
        result = _rich_select(["option1", "option2"])
        assert result is None


def test_rich_select_handles_non_numeric_input():
    """Test that _rich_select handles non-numeric input."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="invalid"):
        result = _rich_select(["option1", "option2"])
        assert result is None


def test_rich_select_handles_keyboard_interrupt():
    """Test that _rich_select handles KeyboardInterrupt gracefully."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", side_effect=KeyboardInterrupt):
        result = _rich_select(["option1", "option2"])
        assert result is None


def test_rich_select_returns_list_when_multi():
    """Test that _rich_select returns list when multi=True."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="1"):
        result = _rich_select(["option1", "option2"], multi=True)
        assert result == ["option1"]


# Tests for select_1 and exit_0 options


def test_rich_select_with_select_1_auto_selects_single_choice():
    """Test that _rich_select auto-selects when only one choice and select_1=True."""
    result = _rich_select(["only_option"], select_1=True)
    assert result == "only_option"


def test_rich_select_with_select_1_shows_menu_for_multiple_choices():
    """Test that _rich_select shows menu when multiple choices even with select_1=True."""
    with patch("invoke_toolkit.utils.fzf.Prompt.ask", return_value="1"):
        result = _rich_select(["option1", "option2"], select_1=True)
        assert result == "option1"


def test_rich_select_with_select_1_multi_returns_list():
    """Test that _rich_select returns list when select_1=True and multi=True."""
    result = _rich_select(["only_option"], select_1=True, multi=True)
    assert result == ["only_option"]


def test_rich_select_with_exit_0_returns_none_for_empty_choices():
    """Test that _rich_select returns None when no choices and exit_0=True."""
    result = _rich_select([], exit_0=True)
    assert result is None


def test_rich_select_with_exit_0_returns_empty_list_for_empty_choices_multi():
    """Test that _rich_select returns empty list when no choices, exit_0=True, and multi=True."""
    result = _rich_select([], exit_0=True, multi=True)
    assert not result


def test_select_passes_select_1_to_fzf():
    """Test that select passes select_1 option to fzf command."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch(
            "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result
        ) as mock_run:
            select(ctx, ["option1", "option2"], select_1=True)

            call_args = mock_run.call_args[0][0]
            assert "--select-1" in call_args


def test_select_passes_exit_0_to_fzf():
    """Test that select passes exit_0 option to fzf command."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch(
            "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result
        ) as mock_run:
            select(ctx, ["option1", "option2"], exit_0=True)

            call_args = mock_run.call_args[0][0]
            assert "--exit-0" in call_args


def test_select_with_select_1_uses_fallback_correctly():
    """Test that select uses fallback with select_1 when fzf not available."""
    ctx = Context()

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch("invoke_toolkit.utils.fzf._show_fzf_warning"):
            with patch(
                "invoke_toolkit.utils.fzf._rich_select", return_value="only_option"
            ) as mock_rich:
                result = select(ctx, ["only_option"], use_fallback=True, select_1=True)

                # Should call rich_select with select_1=True
                mock_rich.assert_called_once_with(
                    ["only_option"], "Select an option", False, True, False
                )
                assert result == "only_option"


def test_select_with_exit_0_uses_fallback_correctly():
    """Test that select uses fallback with exit_0 when fzf not available."""
    ctx = Context()

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch("invoke_toolkit.utils.fzf._show_fzf_warning"):
            with patch(
                "invoke_toolkit.utils.fzf._rich_select", return_value=None
            ) as mock_rich:
                result = select(ctx, [], use_fallback=True, exit_0=True)

                # Should call rich_select with exit_0=True
                mock_rich.assert_called_once_with(
                    [], "Select an option", False, False, True
                )
                assert result is None


def test_select_from_command_passes_select_1_to_fzf():
    """Test that select_from_command passes select_1 option to fzf command."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "result"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 0
    mock_fzf_result.stdout = "result"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ) as mock_fzf:
                select_from_command(ctx, "echo test", select_1=True)

                call_args = mock_fzf.call_args[0][0]
                assert "--select-1" in call_args


def test_select_from_command_passes_exit_0_to_fzf():
    """Test that select_from_command passes exit_0 option to fzf command."""
    ctx = Context()
    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "result"

    mock_fzf_result = Mock()
    mock_fzf_result.returncode = 0
    mock_fzf_result.stdout = "result"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch(
                "invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_fzf_result
            ) as mock_fzf:
                select_from_command(ctx, "echo test", exit_0=True)

                call_args = mock_fzf.call_args[0][0]
                assert "--exit-0" in call_args


def test_select_from_command_with_select_1_uses_fallback_correctly():
    """Test that select_from_command uses fallback with select_1 when fzf not available."""
    ctx = Context()
    mock_result = Mock()
    mock_result.ok = True
    mock_result.stdout = "only_result\n"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch.object(ctx, "run", return_value=mock_result):
            with patch("invoke_toolkit.utils.fzf._show_fzf_warning"):
                with patch(
                    "invoke_toolkit.utils.fzf._rich_select", return_value="only_result"
                ) as mock_rich:
                    result = select_from_command(
                        ctx, "echo test", use_fallback=True, select_1=True
                    )

                    # Should call rich_select with select_1=True
                    call_args = mock_rich.call_args[0]
                    assert call_args[0] == ["only_result"]
                    # Check positional args: choices, prompt, multi, select_1, exit_0
                    assert mock_rich.call_args[0][3] is True  # select_1
                    assert result == "only_result"


# Tests for fzf warning message


def test_show_fzf_warning_displays_message(capsys):
    """Test that warning message is displayed when fzf is not available."""
    ctx = Context()

    # Reset the global warning flag
    import invoke_toolkit.utils.fzf as fzf_module

    fzf_module._fzf_warning_shown = False

    _show_fzf_warning(ctx, force_fallback=False)

    # Check stderr output
    captured = capsys.readouterr()
    assert "fzf not found" in captured.err
    assert "https://github.com/junegunn/fzf" in captured.err
    assert "fuzzy_finder.show_warnings = false" in captured.err


def test_show_fzf_warning_only_shows_once(capsys):
    """Test that warning is only shown once per session."""
    ctx = Context()

    # Reset the global warning flag
    import invoke_toolkit.utils.fzf as fzf_module

    fzf_module._fzf_warning_shown = False

    # Call twice
    _show_fzf_warning(ctx, force_fallback=False)
    _show_fzf_warning(ctx, force_fallback=False)

    # Check that message only appears once
    captured = capsys.readouterr()
    # Count occurrences of the warning message
    occurrences = captured.err.count("fzf not found")
    assert occurrences == 1


def test_show_fzf_warning_respects_config(capsys):
    """Test that warning can be disabled via config."""
    ctx = Context()
    ctx.config._config["fuzzy_finder"] = {"show_warnings": False}

    # Reset the global warning flag
    import invoke_toolkit.utils.fzf as fzf_module

    fzf_module._fzf_warning_shown = False

    _show_fzf_warning(ctx, force_fallback=False)

    # Should not output anything when warnings disabled
    captured = capsys.readouterr()
    assert captured.err == ""


def test_select_shows_warning_when_using_fallback():
    """Test that select shows warning when falling back to rich selector."""
    ctx = Context()

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch("invoke_toolkit.utils.fzf._rich_select", return_value="option1"):
            with patch("invoke_toolkit.utils.fzf._show_fzf_warning") as mock_warning:
                # Reset the global warning flag
                import invoke_toolkit.utils.fzf as fzf_module

                fzf_module._fzf_warning_shown = False

                select(ctx, ["option1", "option2"], use_fallback=True)

                # Should call warning function
                mock_warning.assert_called_once_with(ctx, force_fallback=False)


def test_select_from_command_shows_warning_when_using_fallback():
    """Test that select_from_command shows warning when falling back."""
    ctx = Context()
    mock_result = Mock()
    mock_result.ok = True
    mock_result.stdout = "option1\noption2\n"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=False):
        with patch.object(ctx, "run", return_value=mock_result):
            with patch("invoke_toolkit.utils.fzf._rich_select", return_value="option1"):
                with patch(
                    "invoke_toolkit.utils.fzf._show_fzf_warning"
                ) as mock_warning:
                    # Reset the global warning flag
                    import invoke_toolkit.utils.fzf as fzf_module

                    fzf_module._fzf_warning_shown = False

                    select_from_command(ctx, "echo test", use_fallback=True)

                    # Should call warning function
                    mock_warning.assert_called_once_with(ctx, force_fallback=False)


def test_warning_not_shown_when_fzf_available():
    """Test that no warning is shown when fzf is available."""
    ctx = Context()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "option1"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch("invoke_toolkit.utils.fzf.subprocess.run", return_value=mock_result):
            with patch("invoke_toolkit.utils.fzf._show_fzf_warning") as mock_warning:
                select(ctx, ["option1", "option2"])

                # Should not call warning function
                mock_warning.assert_not_called()


def test_select_respects_force_fallback_config():
    """Test that select uses fallback when force_fallback is enabled in config."""
    ctx = Context()
    ctx.config._config["fuzzy_finder"] = {"force_fallback": True}

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch("invoke_toolkit.utils.fzf._show_fzf_warning") as mock_warning:
            with patch(
                "invoke_toolkit.utils.fzf._rich_select", return_value="option1"
            ) as mock_rich:
                result = select(ctx, ["option1", "option2"], use_fallback=True)

                # Should use rich fallback even though fzf is available
                mock_rich.assert_called_once()
                # Should show warning with force_fallback=True
                mock_warning.assert_called_once_with(ctx, force_fallback=True)
                assert result == "option1"


def test_select_from_command_respects_force_fallback_config():
    """Test that select_from_command uses fallback when force_fallback is enabled."""
    ctx = Context()
    ctx.config._config["fuzzy_finder"] = {"force_fallback": True}

    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "option1\noption2\noption3"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.object(ctx, "run", return_value=mock_cmd_result):
            with patch("invoke_toolkit.utils.fzf._show_fzf_warning") as mock_warning:
                with patch(
                    "invoke_toolkit.utils.fzf._rich_select", return_value="option2"
                ) as mock_rich:
                    result = select_from_command(ctx, "echo test", use_fallback=True)

                    # Should use rich fallback even though fzf is available
                    mock_rich.assert_called_once()
                    # Should show warning with force_fallback=True
                    mock_warning.assert_called_once_with(ctx, force_fallback=True)
                    assert result == "option2"


def test_force_fallback_with_use_fallback_false_still_raises():
    """Test that force_fallback with use_fallback=False still raises error."""
    ctx = Context()
    ctx.config._config["fuzzy_finder"] = {"force_fallback": True}

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with pytest.raises(RuntimeError, match="fzf is not installed"):
            select(ctx, ["option1", "option2"], use_fallback=False)


def test_select_respects_force_fallback_env_var():
    """Test that select uses fallback when INVOKE_FUZZY_FINDER_FORCE_FALLBACK is set."""
    from invoke_toolkit import Config

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.dict("os.environ", {"INVOKE_FUZZY_FINDER_FORCE_FALLBACK": "1"}):
            # Create config and load shell env to pick up the env var
            config = Config()
            config.load_shell_env()
            ctx = Context(config)

            with patch("invoke_toolkit.utils.fzf._show_fzf_warning") as mock_warning:
                with patch(
                    "invoke_toolkit.utils.fzf._rich_select", return_value="option1"
                ) as mock_rich:
                    result = select(ctx, ["option1", "option2"], use_fallback=True)

                    assert result == "option1"
                    mock_rich.assert_called_once()
                    mock_warning.assert_called_once_with(ctx, force_fallback=True)


def test_select_from_command_respects_force_fallback_env_var():
    """Test that select_from_command uses fallback when env var is set."""
    from invoke_toolkit import Config

    mock_cmd_result = Mock()
    mock_cmd_result.ok = True
    mock_cmd_result.stdout = "option1\noption2\noption3"

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.dict("os.environ", {"INVOKE_FUZZY_FINDER_FORCE_FALLBACK": "true"}):
            # Create config and load shell env to pick up the env var
            config = Config()
            config.load_shell_env()
            ctx = Context(config)

            with patch.object(ctx, "run", return_value=mock_cmd_result):
                with patch(
                    "invoke_toolkit.utils.fzf._show_fzf_warning"
                ) as mock_warning:
                    with patch(
                        "invoke_toolkit.utils.fzf._rich_select", return_value="option1"
                    ) as mock_rich:
                        result = select_from_command(
                            ctx, "ls", prompt="Select", use_fallback=True
                        )

                        assert result == "option1"
                        mock_rich.assert_called_once()
                        mock_warning.assert_called_once_with(ctx, force_fallback=True)


def test_env_var_overrides_config():
    """Test that INVOKE_FUZZY_FINDER_FORCE_FALLBACK env var overrides config."""
    from invoke_toolkit import Config

    with patch("invoke_toolkit.utils.fzf.is_fzf_available", return_value=True):
        with patch.dict("os.environ", {"INVOKE_FUZZY_FINDER_FORCE_FALLBACK": "1"}):
            # Create config and load shell env to pick up the env var
            config = Config()
            config.load_shell_env()
            ctx = Context(config)

            # Verify the env var was loaded into config
            assert ctx.config.fuzzy_finder.force_fallback is True

            with patch("invoke_toolkit.utils.fzf._show_fzf_warning") as mock_warning:
                with patch(
                    "invoke_toolkit.utils.fzf._rich_select", return_value="option1"
                ) as mock_rich:
                    result = select(ctx, ["option1", "option2"], use_fallback=True)

                    assert result == "option1"
                    mock_rich.assert_called_once()
                    mock_warning.assert_called_once_with(ctx, force_fallback=True)
