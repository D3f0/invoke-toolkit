# TODO: Move this functionality to the program since it's too late to expand the collection
# in a task
import re
from enum import Enum, auto
from itertools import chain
from pathlib import Path
from shutil import rmtree
from textwrap import dedent

from invoke_toolkit.task import task
from invoke_toolkit.context import Context

from invoke_toolkit.output import console, rich_exit
from invoke_toolkit.program import InvokeToolkitProgram


def clean_python_name(a_name: str) -> str:
    # Remove invalid characters
    valid_characters = re.sub("[^0-9a-zA-Z_]", "_", a_name)

    # Remove leading characters until we find a letter or underscore
    leading_letter_name = re.sub("^[^a-zA-Z_]+", "", valid_characters)
    return leading_letter_name


@task(default=True, name="list")
def list_(ctx: Context):
    """List plugins"""


@task()
def add(ctx: Context, plugin_spec: str) -> None:
    """Add a plugin"""
    ...


@task()
def remove(ctx: Context, name: str) -> None:
    """Add a plugin"""


class PluginTypes(str, Enum):
    DIR = auto()
    FILE = auto()


PLUGIN_ARGUMENT_ALIASES = {
    PluginTypes.DIR: ["d", "dir", "folder"],
    PluginTypes.FILE: [
        "f",
        "file",
    ],
}
_HUMAN_READABLE = ",".join(x for x in chain(*PLUGIN_ARGUMENT_ALIASES.values()))


@task(
    help={
        "name": "The name of the plugin",
        "destination_": "Where to create the plugin files",
        "type_": "The invoke collection type, it can be a single file "
        f"(options: {_HUMAN_READABLE})",
    }
)
def create(
    ctx: Context,
    name_: str = None,
    type_: str = "",
    destination_="./plugins/",
) -> None:
    """Create a plugin of a specific type, tasks.py is the simplest one, but can also
    be a folder with name/__init__.py
    """
    destination = Path(destination_)
    if not destination.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
    p_type = PLUGIN_ARGUMENT_ALIASES.get(type_) if type_ else PluginTypes.FILE
    if not isinstance(p_type, PluginTypes):
        rich_exit(f"No plugin type found: {type_}")
    name = clean_python_name(name_)
    path = destination / name
    try:
        path.mkdir(exist_ok=False)
    except FileExistsError:
        rich_exit(f"Plugin {name} already exists at {destination}")
    console.print(
        f"🔌  Creating plugin [yellow]{name}[/yellow]  in {path} ([red]{p_type}[/red])"
    )
    if p_type == PluginTypes.FILE:
        tasks_py = path / "tasks.py"
        tasks_py.write_text(
            dedent(
                f"""
                # This is a invoke-toolkit plugin created task file
                # For the task {name}
                from invoke import task, Context

                @task()
                def my_task(ctx: Context):
                    ctx.run("Hello from plugin {name}")

                # @task()
                # def another_task(ctx: Context):
                #    ctx.run("Hello from task another_task")
                """
            )
        )


@task()
def clean(ctx: Context):
    """Remove all the cached plugins"""
    program: InvokeToolkitProgram = ctx.config.get("invoke-toolkit", {}).get("instance")

    for i, name in enumerate(program.plugin_dir.glob("*")):
        console.print(f"Removing [red]{name}[/red]")
        rmtree(program.plugin_dir)
    else:
        print("No plugins to remove")
