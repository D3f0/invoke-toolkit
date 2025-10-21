import pytest
from invoke import Program
from invoke.collection import Collection

from invoke_toolkit import task
from invoke_toolkit.collections import InvokeToolkitCollection
from invoke_toolkit.context.context import InvokeToolkitContext
from invoke_toolkit.program import InvokeToolkitProgram


@task()
def boolean_flag(c: InvokeToolkitContext, flag=True):
    print(flag)


@pytest.mark.parametrize(
    "program_class,collection_class",
    [
        (Program, Collection),
        pytest.param(
            InvokeToolkitProgram,
            InvokeToolkitCollection,
            marks=pytest.mark.skip(reason="TODO: Fix boolean flags set up to True"),
        ),
    ],
)
def test_parsing_boolean_flag(ctx, program_class, collection_class, capsys):
    ns = collection_class()

    ns.add_task(boolean_flag)

    p = program_class(namespace=ns)
    p.run(["", "boolean-flag", "-h"], exit=False)
    capture_result = capsys.readouterr()
    out, _err = capture_result.out, capture_result.err
    assert "-f, --[no-]flag" in out
