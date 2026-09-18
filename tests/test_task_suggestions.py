from typing import Any, cast

from invoke.tasks import Task
from invoke_toolkit import task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.testing import TestingToolkitProgram


def collection(*tasks, name: str | None = None) -> ToolkitCollection:
    namespace = ToolkitCollection(name) if name else ToolkitCollection()
    for decorated_task in tasks:
        namespace.add_task(cast(Task[Any], decorated_task))
    return namespace


def root_with(*collections: ToolkitCollection) -> ToolkitCollection:
    namespace = ToolkitCollection()
    for child in collections:
        namespace.add_collection(child)
    return namespace


MISSPELLED_BUILD = "build".replace("l", "")


def test_unknown_task_suggests_close_task_name(capsys):
    @task
    def build(ctx):
        pass

    program = TestingToolkitProgram(namespace=collection(build))
    program.run(["", MISSPELLED_BUILD], exit=False)
    output = capsys.readouterr().err

    assert f"No idea what '{MISSPELLED_BUILD}' is!" in output
    assert "Did you mean 'build'?" in output


def test_unknown_task_does_not_suggest_distant_task(capsys):
    @task
    def build(ctx):
        pass

    program = TestingToolkitProgram(namespace=collection(build))
    program.run(["", "deploy"], exit=False)
    output = capsys.readouterr().err

    assert "No idea what 'deploy' is!" in output
    assert "Did you mean" not in output


def test_unknown_nested_task_suggests_full_task_name(capsys):
    @task
    def build(ctx):
        pass

    tools = collection(build, name="tools")
    program = TestingToolkitProgram(namespace=root_with(tools))
    program.run(["", f"tools.{MISSPELLED_BUILD}"], exit=False)
    output = capsys.readouterr().err

    assert f"No idea what 'tools.{MISSPELLED_BUILD}' is!" in output
    assert "Did you mean" in output
    assert "'tools.build'" in output


def test_unknown_collection_suggests_close_collection_name(capsys):
    @task
    def build(ctx):
        pass

    tools = collection(build, name="tools")
    program = TestingToolkitProgram(namespace=root_with(tools))
    program.run(["", "tolos"], exit=False)
    output = capsys.readouterr().err

    assert "No idea what 'tolos' is!" in output
    assert "Did you mean 'tools'?" in output


def test_unknown_nested_collection_suggests_full_collection_name(capsys):
    @task
    def deploy(ctx):
        pass

    aws = collection(deploy, name="aws")
    plugins = root_with(aws)
    plugins.name = "plugins"
    program = TestingToolkitProgram(namespace=root_with(plugins))
    program.run(["", "plugins.awz"], exit=False)
    output = capsys.readouterr().err

    assert "No idea what 'plugins.awz' is!" in output
    assert "'plugins.aws'" in output


def test_unknown_task_alias_suggests_close_alias(capsys):
    @task(aliases=["compile"])
    def build(ctx):
        pass

    program = TestingToolkitProgram(namespace=collection(build))
    program.run(["", "compiel"], exit=False)
    output = capsys.readouterr().err

    assert "No idea what 'compiel' is!" in output
    assert "'compile'" in output


def test_unknown_help_task_suggests_close_task_name(capsys):
    @task
    def build(ctx):
        pass

    program = TestingToolkitProgram(namespace=collection(build))
    program.run(["", "--help", MISSPELLED_BUILD], exit=False)
    output = capsys.readouterr().err

    assert f"No idea what '{MISSPELLED_BUILD}' is!" in output
    assert "Did you mean 'build'?" in output
