"""Tests for self-referential alias guard in @task."""

import warnings

import pytest
from invoke import Collection

from invoke_toolkit.tasks.tasks import task


def _make_collection(*tasks):
    c = Collection()
    for t in tasks:
        c.add_task(t)
    return c


# ---------------------------------------------------------------------------
# Warning is emitted
# ---------------------------------------------------------------------------


def test_warns_when_alias_matches_function_name_underscore():
    """Alias equal to the function name (underscore form) triggers a UserWarning."""
    with pytest.warns(UserWarning, match="match the task name"):

        @task(aliases=["my_task"])
        def my_task(ctx):
            pass


def test_warns_when_alias_matches_function_name_hyphen():
    """Alias equal to the hyphenated function name triggers a UserWarning."""
    with pytest.warns(UserWarning, match="match the task name"):

        @task(aliases=["my-task"])
        def my_task(ctx):
            pass


def test_warns_when_alias_matches_explicit_name():
    """Alias equal to an explicit name= override triggers a UserWarning."""
    with pytest.warns(UserWarning, match="match the task name"):

        @task(name="deploy", aliases=["deploy"])
        def run_deploy(ctx):
            pass


# ---------------------------------------------------------------------------
# Self-referential alias is stripped (no RecursionError)
# ---------------------------------------------------------------------------


def test_self_alias_stripped_task_is_reachable():
    """After stripping the self-alias the task is still reachable by its name."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)

        @task(aliases=["my_task"])
        def my_task(ctx):
            pass

    c = _make_collection(my_task)
    # Must not raise RecursionError
    resolved = c["my-task"]
    assert resolved is not None


def test_self_alias_stripped_valid_aliases_kept():
    """Valid aliases are preserved; only the self-referential one is removed."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)

        @task(aliases=["my_task", "mt"])
        def my_task(ctx):
            pass

    c = _make_collection(my_task)
    assert c["mt"] is not None
    assert c["my-task"] is not None


def test_all_aliases_self_referential_no_aliases_registered():
    """When every alias is self-referential the task has no aliases."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)

        @task(aliases=["my_task3"])
        def my_task3(ctx):
            pass

    c = _make_collection(my_task3)
    # task_names maps canonical name → list of aliases; list should be empty
    assert c.task_names["my-task3"] == []


def test_no_warning_for_distinct_alias():
    """A genuinely distinct alias produces no warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)  # would raise if a warning fires

        @task(aliases=["mt"])
        def my_task(ctx):
            pass

    c = _make_collection(my_task)
    assert c["mt"] is not None
