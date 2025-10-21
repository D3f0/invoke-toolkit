import pytest
from pathlib import Path
from textwrap import dedent
from typing import Any, Union

from pytest import TempPathFactory
from tomlkit import TOMLDocument, dump, parse

from invoke_toolkit import Context

from invoke_toolkit.loader.entrypoint import COLLECTION_ENTRY_POINT


def add_entrypoint(pth: Union[str, Path], name: str, value: Any) -> None:
    """Adds an entry-point to a pyproject.toml file defined by pth"""
    if isinstance(pth, (str, Path)):
        with open(pth, encoding="utf-8") as fp:
            toml: TOMLDocument = parse(fp.read())
    else:
        raise ValueError(pth)
    entry_points = toml["project"].setdefault("entry-points", {})
    entry_points[name] = value
    with open(pth, mode="w", encoding="utf-8") as fp:
        dump(toml, fp)


@pytest.mark.skip(reason="API not yet defined")
def test_loader_from_entrypoints(
    package_in_venv, ctx: Context, tmp_path_factory: TempPathFactory
):
    """
    Checks that the project that have a pyproject.toml with some collections
    are loaded in the namespace
    """
    ctx.run("uv pip list | grep invoke-toolkit")
    plugin_src_root = tmp_path_factory.mktemp("package_1")
    name = "a_plugin"
    with ctx.cd(plugin_src_root):
        ctx.run(f"uv init --package {name} --python 3.11")
        plugin__init__loc: str = ctx.run(
            f"find {plugin_src_root} -type f -name __init__.py"
        ).stdout.strip()
        plugin_package_path = plugin_src_root / name
        plugin__init__ = Path(plugin__init__loc)
        plugin__init__.write_text(
            dedent(
                """
                from invoke_toolkit import task, Context
                
                @task()
                def hello(ctx: Context):
                    ctx.run("echo hello")
                """
            ),
            encoding="utf-8",
        )

        plugin_toml_path = Path(plugin_package_path / "pyproject.toml")
        add_entrypoint(plugin_toml_path, COLLECTION_ENTRY_POINT, {name: name})

        with ctx.cd(plugin_package_path):
            res = ctx.run("uv venv && uv pip install -e .", warn=True)
            assert res.ok, res.stderr
        # import os

        # os.system(f"yazi {plugin_toml_path.parent}")
    result = ctx.run(f"uv pip install -e {plugin_package_path}", warn=True)
    assert result.ok, "Failed to install editable plugin package"
    res = ctx.run("it -l", pty=False, warn=True)
    assert res.ok, res.stderr
