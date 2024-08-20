import pytest
import json
from typing import List
from invoke.context import Context
from typing_extensions import TypedDict


class PipListJsonOutput(TypedDict):
    name: str
    version: str


@pytest.mark.slow
def test_package(package, venv, ctx: Context):
    ctx.run(f"{venv.python} -m pip install {package}")
    installed_json_output = ctx.run(f"{venv.python} -m pip list --format json").stdout
    installed_list: List[PipListJsonOutput] = json.loads(installed_json_output)
    installed_dict = {element["name"]: element["version"] for element in installed_list}
    assert "invoke-toolkit" in installed_dict
