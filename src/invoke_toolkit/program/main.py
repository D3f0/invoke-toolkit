"""Entrypoint for project.scripts"""

from invoke_toolkit.loader.entrypoint import EntryPointLoader

from .program import ToolkitProgram

program = ToolkitProgram(name="invoke-toolkit", loader_class=EntryPointLoader)
