"""Call stack inspection"""

import inspect
from pathlib import Path
from typing import Optional

from invoke.util import debug
from invoke_toolkit.output import get_console


# def print_call_stack():
#     """Prints the current call stack."""
#     for frame_info in inspect.stack():
#         filename, lineno, function, code_context, index = frame_info
#         print(f"File: {filename}, Line: {lineno}, Function: {function}")


def print_rich_frames(frames: list):
    """Show frames in rich format"""
    get_console().print(frames)


def get_calling_file_path(find_call_text: str) -> Optional[str]:
    """Returns the containing folder of the module where the find_call_text is located"""

    # Get the frame object of the caller
    start_offset = 2
    stack = inspect.stack()
    index_frame_dict = dict(enumerate(stack[start_offset:]))
    # print_rich_frames(stack[:2])
    # ...
    # print_rich_frames(index_frame_dict)
    frame = None
    found = False
    for i, frame in index_frame_dict.items():
        if any(find_call_text in line for line in frame.code_context):
            debug(f"Found '{find_call_text}' in {frame}, call offset {i + 2}")
            found = True
            break
    if not found:
        return None
    # Get the module object of the caller
    containing_directory = str(Path(frame.filename).parent.parent)
    return containing_directory
