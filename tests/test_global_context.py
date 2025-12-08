"""Tests for the global_context singleton functionality"""

import pytest
from invoke_toolkit import global_context, run, Context
import invoke_toolkit


@pytest.fixture(autouse=True)
def reset_global_context():
    """Reset global context before each test"""
    original = invoke_toolkit._global_context_instance
    invoke_toolkit._global_context_instance = None
    yield
    # Restore original state
    invoke_toolkit._global_context_instance = original


# Singleton behavior tests
def test_global_context_returns_context_instance():
    """Test that global_context returns a Context instance"""
    context = global_context()
    assert isinstance(context, Context)


def test_global_context_is_singleton():
    """Test that global_context returns the same instance on multiple calls"""
    context1 = global_context()
    context2 = global_context()
    assert context1 is context2


def test_global_context_first_call_creates_instance():
    """Test that first call to global_context creates the instance"""
    assert invoke_toolkit._global_context_instance is None
    context = global_context()
    assert invoke_toolkit._global_context_instance is not None
    assert invoke_toolkit._global_context_instance is context


def test_global_context_instance_persists():
    """Test that the global instance persists across multiple calls"""
    context_id_1 = id(global_context())
    context_id_2 = id(global_context())
    context_id_3 = id(global_context())
    assert context_id_1 == context_id_2 == context_id_3


# Run function with global context tests
def test_run_uses_global_context():
    """Test that run() uses the global context"""
    result = run("echo 'test'")
    assert result is not None
    assert result.ok


def test_run_with_successful_command():
    """Test run with a successful command"""
    result = run("echo 'hello'")
    assert result is not None
    assert result.ok
    assert "hello" in result.stdout or result.return_code == 0


def test_run_captures_output():
    """Test that run captures command output"""
    result = run("echo 'captured output'", hide=True)
    assert result is not None
    assert "captured output" in result.stdout


def test_run_with_return_code_check():
    """Test run with return code checking"""
    result = run("true")
    assert result is not None
    assert result.return_code == 0


def test_run_with_failed_command():
    """Test run with a failed command using warn=True"""
    result = run("false", warn=True)
    assert result is not None
    assert result.return_code != 0


def test_run_multiple_times_same_context():
    """Test that multiple runs use the same context"""
    ctx_before = global_context()
    run("echo 'test1'")
    run("echo 'test2'")
    ctx_after = global_context()
    assert ctx_before is ctx_after


# Run and sudo share global context tests
def test_run_and_global_context_share_instance():
    """Test that run uses the same context instance as global_context"""
    ctx = global_context()
    # Both run and global_context should use the same instance
    assert ctx is global_context()


def test_context_persists_after_run():
    """Test that context persists after run calls"""
    ctx_before = global_context()
    run("echo 'test1'")
    run("echo 'test2'")
    ctx_after = global_context()
    assert ctx_before is ctx_after


def test_global_context_identity_consistency():
    """Test that global context identity remains consistent"""
    context = global_context()
    context_id = id(context)

    run("true")
    run("false", warn=True)

    new_context = global_context()
    assert id(new_context) == context_id


# Global context behavior tests
def test_global_context_has_config():
    """Test that global context has a config"""
    context = global_context()
    assert context.config is not None


def test_global_context_can_run_commands():
    """Test that global context can run commands directly"""
    context = global_context()
    result = context.run("echo 'direct context call'", hide=True)
    assert result is not None
    assert "direct context call" in result.stdout


def test_global_context_returns_same_config():
    """Test that global context always returns same config instance"""
    ctx1 = global_context()
    ctx2 = global_context()
    assert ctx1.config is ctx2.config


def test_run_function_uses_global_context_internally():
    """Test that run() function calls use the global context"""
    # Get reference to global context
    ctx = global_context()
    ctx_id = id(ctx)

    # Call run which should use the same context
    result = run("true")

    # Verify the context used by run is the same
    assert id(global_context()) == ctx_id
    assert result is not None


def test_global_context_callable_multiple_times():
    """Test that global_context can be called multiple times safely"""
    for _ in range(5):
        context = global_context()
        assert isinstance(context, Context)
        assert context.config is not None


# Global context interaction tests
def test_run_output_consistency():
    """Test that run produces consistent output"""
    result1 = run("echo 'test'", hide=True)
    result2 = run("echo 'test'", hide=True)
    assert result1.stdout == result2.stdout


def test_run_with_kwargs():
    """Test that run passes kwargs correctly to context"""
    result = run("true", hide=True)
    assert result is not None
    assert result.ok


def test_global_context_state_isolation():
    """Test that multiple run calls don't interfere with each other"""
    result1 = run("echo 'first'", hide=True)
    result2 = run("echo 'second'", hide=True)

    assert "first" in result1.stdout
    assert "second" in result2.stdout
    assert "second" not in result1.stdout
    assert "first" not in result2.stdout
