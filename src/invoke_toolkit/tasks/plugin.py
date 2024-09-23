# TODO: Move this functionality to the program since it's too late to expand the collection
# in a task
from itertools import chain
from pathlib import Path
from textwrap import dedent
from typing import Optional
from invoke.collection import Collection
from invoke import Context, task
import re
from enum import Enum, auto
from invoke_toolkit.output import rich_exit, console
from invoke_toolkit.program import InvokeToolkitProgram
from rich.table import Table
from invoke.util import helpline
from shutil import rmtree
from urllib.parse import urlparse


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


@task(name="with", help={"force": "Force re-fresh plugins"})
def with_(ctx: Context, plugin_ref: str, force=False) -> None:
    """
    Add a repo to the Collections for one-shot runs like CI pipelines.
    """
    program: Optional[InvokeToolkitProgram] = ctx.get("invoke-toolkit", {}).get(
        "instance"
    )
    if program is None:
        rich_exit("Can't access the program. Likely it's not a InvokeToolkit program")
    elif not isinstance(program, InvokeToolkitProgram):
        console.log("The program instance is not a subclass of InvokeToolkit.")

    try:
        parsed = urlparse(plugin_ref)

        org, name = parsed.path.strip("/").split("/")[:2]
        name, *_ = name.split(".")
        target_dir = program.plugin_dir / f"{org}_{name}"
        if target_dir.exists() and not force:
            print("Plugin already available...")
        else:
            target_dir.mkdir(parents=True)
            console.print(f"Getting plugin from {plugin_ref} ([yellow]git[/yellow])")
            # FIXME: We need to let know we need git here
            ctx.run(f"git clone {plugin_ref} '{target_dir}'")
        console.print(f"Loading tasks from '{target_dir}'")
        program.collection.load_directory(target_dir)

    except Exception as error:
        console.print_exception(show_locals=True)
        rich_exit(f"Can't handle {plugin_ref} yet: {error=}")


@task()
def tasks(ctx: Context):
    """Lists tasks after the program has been instantiated, use with plugin.with"""
    program: Optional[InvokeToolkitProgram] = ctx.get("invoke-toolkit", {}).get(
        "instance"
    )
    if program is None:
        rich_exit("Can't access the program. Likely it's not a InvokeToolkit program")

    collections = program.collection.collections
    console.print("[green]Subcommands[/green]\n")
    table = Table(title="Available tasks", row_styles=["", "dim"], box=None)

    table.add_column("Task")
    table.add_column("Help")

    for name, items in collections.items():
        # console.print(f"{sep}[yellow bold]{name}[/yellow bold]")
        if isinstance(items, Collection):
            for item, likely_task in items.tasks.items():
                # console.print(f"{sep * 2}{name}.{item}")

                table.add_row(f"{name}.{item}", helpline(likely_task))
        else:
            console.print(f"{type(items)}")
    console.print(table)


@task()
def clean(ctx: Context):
    """Remove all the downloaded plugins"""
    program: InvokeToolkitProgram = ctx.config.get("invoke-toolkit", {}).get("instance")

    for i, name in enumerate(program.plugin_dir.glob("*")):
        console.print(f"Removing [red]{name}[/red]")
        rmtree(program.plugin_dir)
    else:
        print("No plugins to remove")
