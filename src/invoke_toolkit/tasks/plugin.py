from pathlib import Path
from invoke import Context, task
import re
from invoke_toolkit.output import rich_exit, console


def clean_python_name(a_name: str) -> str:
    # Remove invalid characters
    valid_characters = re.sub("[^0-9a-zA-Z_]", "_", a_name)

    # Remove leading characters until we find a letter or underscore
    leading_letter_name = re.sub("^[^a-zA-Z_]+", "", valid_characters)
    return leading_letter_name


@task(default=True)
def list_(ctx: Context):
    """List plugins"""


@task()
def add(ctx: Context, plugin_spec: str) -> None:
    """Add a plugin"""


@task()
def remove(ctx: Context, name: str) -> None:
    """Add a plugin"""


@task(
    help={
        "name": "The name of the plugin",
        "path": "Where to create the plugin files",
    }
)
def create(ctx: Context, name_: str, path_: str = ".") -> None:
    """Create a plugin"""
    path = Path(path_)
    if not path.is_dir():
        rich_exit("[red][/red] is not a valid directory")
    name = clean_python_name(name_)
    console.print(f"🔌  Creating plugin [yellow]{name}[/yellow]  in {path}")
