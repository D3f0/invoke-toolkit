"""
Text related utility functions
"""

from io import StringIO
from textwrap import dedent


class DedentedStringIO(StringIO):
    """A StringIO class that dedents the input"""

    def __init__(self, initial_value="", newline="\n"):
        initial_value = dedent(initial_value)
        super().__init__(initial_value, newline)
