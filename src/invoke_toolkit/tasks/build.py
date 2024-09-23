"""
Generate self contained distributable script using some Python
package for stand alone zipped code redistributables
"""

from invoke import task, Context
from invoke_toolkit.output import console


@task(default=True)
def build(ctx: Context):
    """
    Builds a distributable self contained Python based executable
    using shiv
    """
    console.print("[underline]Not yet implemented[/underline]")
