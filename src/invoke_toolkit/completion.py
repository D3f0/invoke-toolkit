"""
Custom completion support for Enum and Literal parameter choices.

This module extends invoke's completion system to support completing
argument values for Enum and Literal parameters.
"""

import glob
import os
import re
import shlex
from typing import List

from invoke.completion.complete import (
    debug,
    print_task_names,
)
from invoke.exceptions import Exit, ParseError
from invoke.parser import Parser, ParserContext

from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.tasks import (
    _extract_enum_params,
    _extract_literal_params,
)
from invoke_toolkit.tasks.types import _FilePathMarker, _FilePatternMarker


def _get_file_completions(
    marker: _FilePathMarker | _FilePatternMarker,
    incomplete: str = "",
) -> List[str]:
    """
    Get file completions based on marker type.

    Args:
        marker: Either a _FilePathMarker or _FilePatternMarker instance
        incomplete: The partial input to filter completions

    Returns:
        List of matching file paths within the current directory boundary
    """
    files: List[str] = []
    cwd = os.path.realpath(".")

    def is_within_cwd(filepath: str) -> bool:
        """Check if filepath is within current working directory."""
        try:
            abs_path = os.path.realpath(filepath)
            # Use commonpath to check if file is under cwd
            common = os.path.commonpath([cwd, abs_path])
            return common == cwd
        except (ValueError, OSError):
            return False

    if isinstance(marker, _FilePathMarker):
        try:
            entries = os.listdir(".")
            files = [f for f in entries if os.path.isfile(f) and is_within_cwd(f)]
        except PermissionError as e:
            debug(f"Permission denied listing current directory: {e}")
            return []
        except OSError as e:
            debug(f"Error listing current directory: {e}")
            return []
    elif isinstance(marker, _FilePatternMarker):
        try:
            raw_files = glob.glob(marker.pattern, recursive=True)
            # Filter to only files within cwd boundary
            files = [f for f in raw_files if os.path.isfile(f) and is_within_cwd(f)]
        except PermissionError as e:
            debug(f"Permission denied with pattern '{marker.pattern}': {e}")
            return []
        except OSError as e:
            debug(f"Error with glob pattern '{marker.pattern}': {e}")
            return []

    # Filter by incomplete prefix with path normalization
    if incomplete:
        incomplete_norm = os.path.normpath(incomplete) if incomplete else ""
        files = [
            f
            for f in files
            if os.path.normpath(f).startswith(incomplete_norm)
            or f.startswith(incomplete)  # Also check raw match for partial inputs
        ]

    return sorted(files)


def get_choices_for_argument(
    collection, context_name: str, arg_name: str, incomplete: str = ""
) -> List[str]:
    """
    Get available choices for an argument in a task.

    Checks in priority order:
    1. Completion callback (if defined)
    2. File completion markers (if defined)
    3. Enum parameters (if defined)
    4. Literal parameters (if defined)

    Args:
        collection: The invoke collection
        context_name: The task name
        arg_name: The argument name (without dashes)
        incomplete: The incomplete value typed by user (for callback filtering)

    Returns:
        List of choice strings, or empty list if no choices defined
    """
    # Try to get the task from the collection
    try:
        task = collection[context_name]
    except KeyError:
        return []

    # Step 1: Check for completion callback (HIGHEST PRIORITY)
    # Callbacks are stored on the Task object, not the body
    if hasattr(task, "_completion_callbacks"):  # pylint: disable=protected-access
        callbacks = task._completion_callbacks  # pylint: disable=protected-access
        if arg_name in callbacks:
            try:
                # Try to call the callback with context and incomplete
                ctx = ToolkitContext()
                result = callbacks[arg_name](ctx, incomplete)
                if result:
                    return [str(choice) for choice in result]
            except (AttributeError, TypeError, ValueError) as e:
                debug(f"Completion callback for {arg_name} failed: {e}")
                # Fall through to next option

    # Step 2: Check for file completion markers (HIGH PRIORITY)
    # File markers are stored on the Task object
    if hasattr(task, "_file_completion_markers"):  # pylint: disable=protected-access
        markers = task._file_completion_markers  # pylint: disable=protected-access
        if arg_name in markers:
            marker = markers[arg_name]
            return _get_file_completions(marker, incomplete)

    # Get the wrapped function if available
    func = task.body
    if hasattr(func, "__wrapped__"):
        func = func.__wrapped__

    # Step 3: Extract enum parameters (MEDIUM PRIORITY)
    enum_params = _extract_enum_params(func)
    if arg_name in enum_params:
        return [str(member.value) for member in enum_params[arg_name]]

    # Step 4: Extract literal parameters (MEDIUM PRIORITY)
    literal_params = _extract_literal_params(func)
    if arg_name in literal_params:
        return [str(v) for v in literal_params[arg_name]]

    return []


def _strip_program_name(names: List[str], remainder: str) -> str:
    """
    Strip the program name from the invocation string.

    Handles cases where the binary name differs from the actual invocation name.

    Args:
        names: List of possible program names
        remainder: The full invocation string

    Returns:
        The invocation string with program name stripped
    """
    # First try exact regex match with escaped names
    invocation = re.sub(
        r"^({}) ".format("|".join(re.escape(n) for n in names)), "", remainder
    )

    # If nothing was stripped, try removing first token
    if invocation == remainder:
        try:
            tokens = shlex.split(remainder)
            if tokens:
                invocation = " ".join(tokens[1:])
        except ValueError:
            pass

    return invocation


def _handle_flag_completion(
    context: ParserContext,
    flag_name: str,
    collection,
) -> bool:
    """
    Handle completion for a flag that takes a value.

    Args:
        context: The parser context
        flag_name: The flag name (e.g., '--color')
        collection: The invoke collection

    Returns:
        True if choices were printed, False otherwise
    """
    flag = context.flags[flag_name]
    if not flag.takes_value:
        # Boolean flags, print task names
        debug("Found, takes no value, printing task names")
        print_task_names(collection)
        return False

    # Try to get choices for this flag
    # Extract the argument name from the flag (e.g., "--color" -> "color")
    arg_name = flag_name.lstrip("-").replace("-", "_")
    task_name = context.name

    if task_name:
        # Extract incomplete value from tokens if available
        incomplete = ""
        choices = get_choices_for_argument(collection, task_name, arg_name, incomplete)
        if choices:
            debug(f"Found choices for {arg_name}: {choices}")
            for choice in choices:
                print(choice)
            return True

    # No choices found, let shell handle it (file completion)
    debug("Found, and it takes a value, so no completion")
    return False


def complete_with_choices(
    names: List[str],
    core,
    initial_context: ParserContext,
    collection,
    parser: Parser,
) -> Exit:
    """
    Enhanced completion function that supports Enum and Literal choices.

    This function extends invoke's basic completion to handle completing
    argument values for parameters with defined choices.
    """
    # Strip out program name
    invocation = _strip_program_name(names, core.remainder)
    debug("Completing for invocation: {!r}".format(invocation))

    # Tokenize
    tokens = shlex.split(invocation)

    # Handle flags (partial or otherwise)
    if tokens and tokens[-1].startswith("-"):
        tail = tokens[-1]
        debug("Invocation's tail {!r} is flag-like".format(tail))

        # Parse invocation to obtain current context
        contexts: List[ParserContext]
        try:
            debug("Seeking context name in tokens: {!r}".format(tokens))
            contexts = parser.parse_argv(tokens)
        except ParseError as e:
            debug(
                "Got parser error ({!r}), grabbing last-seen context {!r}".format(
                    e, e.context
                )
            )
            contexts = [e.context] if e.context is not None else []

        # Fall back to core context if no context seen
        debug("Parsed invocation, contexts: {!r}".format(contexts))
        if not contexts or not contexts[-1]:
            context = initial_context
        else:
            context = contexts[-1]

        debug("Selected context: {!r}".format(context))

        # Check if this flag is known
        debug("Looking for {!r} in {!r}".format(tail, context.flags))
        if tail not in context.flags:
            debug("Not found, completing with flag names")
            # Long flags - partial or just the dashes
            if tail.startswith("--"):
                for name in filter(lambda x: x.startswith("--"), context.flag_names()):
                    print(name)
            # Just a dash, completes with all flags
            elif tail == "-":
                for name in context.flag_names():
                    print(name)
        # Known flags complete w/ values or nothing
        else:
            _handle_flag_completion(context, tail, collection)
    # If not a flag, complete task names
    else:
        debug("Last token isn't flag-like, just printing task names")
        print_task_names(collection)

    raise Exit
