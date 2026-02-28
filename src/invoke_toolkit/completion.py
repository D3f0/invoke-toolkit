"""
Custom completion support for Enum and Literal parameter choices.

This module extends invoke's completion system to support completing
argument values for Enum and Literal parameters.
"""

import glob
import os
import re
import shlex
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import List

from invoke.completion.complete import (
    debug,
    print_task_names,
)
from invoke.exceptions import Exit, ParseError
from invoke.parser import Parser, ParserContext

from invoke_toolkit.config import get_config_value
from invoke_toolkit.context import ToolkitContext
from invoke_toolkit.tasks.tasks import (
    _extract_enum_params,
    _extract_literal_params,
)
from invoke_toolkit.tasks.types import _FileCompletionMarker


def _get_file_completions(
    marker: "_FileCompletionMarker",
    incomplete: str,
) -> List[str]:
    """
    Get file completions based on marker configuration.

    Supports incremental directory traversal:
    - Empty or no `/` → list CWD contents
    - Ends with `/` → list that directory's contents
    - Contains `/` → list parent directory, filter by partial filename

    Args:
        marker: A _FileCompletionMarker instance with completion options
        incomplete: The partial input to filter completions

    Returns:
        List of matching file paths within the current directory boundary
    """
    cwd = os.path.realpath(".")

    def is_within_cwd(filepath: str) -> bool:
        """Check if filepath is within current working directory."""
        try:
            abs_path = os.path.realpath(filepath)
            common = os.path.commonpath([cwd, abs_path])
            return common == cwd
        except (ValueError, OSError):
            return False

    def matches_type_filter(filepath: str) -> bool:
        """Check if filepath matches file_okay/dir_okay filters."""
        is_file = os.path.isfile(filepath)
        is_dir = os.path.isdir(filepath)

        if is_file and not marker.file_okay:
            return False
        if is_dir and not marker.dir_okay:
            return False
        return is_file or is_dir

    # Parse incomplete to determine base directory and filter prefix
    base_dir = "."
    filter_prefix = ""

    if incomplete:
        if incomplete.endswith("/"):
            # User typed "subdir/" → list contents of subdir
            base_dir = incomplete.rstrip("/")
            filter_prefix = ""
        elif "/" in incomplete:
            # User typed "subdir/fil" → list subdir, filter by "fil"
            base_dir = os.path.dirname(incomplete)
            filter_prefix = os.path.basename(incomplete)
        else:
            # User typed "fil" → list CWD, filter by "fil"
            base_dir = "."
            filter_prefix = incomplete

    # Security check: base directory must be within CWD
    if not is_within_cwd(base_dir):
        debug(f"Security: base_dir '{base_dir}' is outside CWD")
        return []

    # Determine prefix to prepend to results
    dir_prefix = "" if base_dir == "." else base_dir + "/"

    files: List[str] = []

    try:
        if marker.pattern:
            # Use glob pattern (patterns are relative to CWD, not base_dir)
            raw_files = glob.glob(marker.pattern, recursive=True)
            # Filter to only files within cwd that match type
            matched_files = [
                f for f in raw_files if is_within_cwd(f) and matches_type_filter(f)
            ]
            # For pattern mode, filter by incomplete prefix
            if incomplete:
                incomplete_norm = os.path.normpath(incomplete) if incomplete else ""
                files = [
                    f
                    for f in matched_files
                    if os.path.normpath(f).startswith(incomplete_norm)
                    or f.startswith(incomplete)
                ]
            else:
                files = matched_files
        else:
            # List entries in base_dir
            entries = os.listdir(base_dir)
            for entry in entries:
                full_path = os.path.join(base_dir, entry) if base_dir != "." else entry
                if not is_within_cwd(full_path):
                    continue
                if not matches_type_filter(full_path):
                    continue
                # Apply filter prefix if present
                if filter_prefix and not entry.startswith(filter_prefix):
                    continue
                # Prepend directory prefix to result
                result_path = dir_prefix + entry
                files.append(result_path)
    except PermissionError as e:
        debug(f"Permission denied: {e}")
        return []
    except OSError as e:
        debug(f"Error listing files: {e}")
        return []

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
    if hasattr(task, "_completion_callbacks"):  # pylint: disable=protected-access,too-many-nested-blocks
        callbacks = task._completion_callbacks  # pylint: disable=protected-access
        if arg_name in callbacks:
            try:
                # Try to call the callback with context and incomplete
                ctx = ToolkitContext()

                # Get timeout from config (default: 10 seconds)
                timeout = get_config_value(
                    ctx, "completion.callback_timeout", default=10.0
                )

                # Execute callback with timeout
                # Note: Don't use context manager because it waits for threads on exit
                executor = ThreadPoolExecutor(max_workers=1)
                try:
                    future = executor.submit(callbacks[arg_name], ctx, incomplete)
                    try:
                        result = future.result(timeout=timeout)
                        if result:
                            return [str(choice) for choice in result]
                    except FuturesTimeoutError:
                        debug(
                            f"Completion callback for {arg_name} timed out after {timeout}s. "
                            f"You can increase this with INVOKE_COMPLETION_CALLBACK_TIMEOUT environment variable."
                        )
                        # Fall through to next option
                finally:
                    # Shutdown without waiting for running threads
                    executor.shutdown(wait=False)
            except (AttributeError, TypeError, ValueError) as e:
                debug(f"Completion callback for {arg_name} failed: {e}")
                # Fall through to next option

    # Step 2: Check for file completion markers (HIGH PRIORITY)
    # File markers are stored on the Task object
    if hasattr(task, "_file_completion_markers"):  # pylint: disable=protected-access
        markers = task._file_completion_markers  # pylint: disable=protected-access
        if arg_name in markers:
            marker = markers[arg_name]
            # Handle all marker types (they all inherit from _FileCompletionMarker now)
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


def _get_directory_completions(incomplete: str) -> List[str]:
    """
    Get directory completions for path arguments like --search-root.

    Args:
        incomplete: The partial path typed by user

    Returns:
        List of matching directory paths
    """
    # Parse incomplete to determine base directory and filter prefix
    base_dir = "."
    filter_prefix = ""

    if incomplete:
        if incomplete.endswith("/"):
            # User typed "subdir/" → list contents of subdir
            base_dir = incomplete.rstrip("/") or "/"
            filter_prefix = ""
        elif "/" in incomplete:
            # User typed "subdir/fil" → list subdir, filter by "fil"
            base_dir = os.path.dirname(incomplete) or "/"
            filter_prefix = os.path.basename(incomplete)
        else:
            # User typed "fil" → list CWD, filter by "fil"
            base_dir = "."
            filter_prefix = incomplete

    # Determine prefix to prepend to results
    if base_dir == ".":
        dir_prefix = ""
    elif base_dir == "/":
        dir_prefix = "/"
    else:
        dir_prefix = base_dir + "/"

    directories: List[str] = []

    try:
        if not os.path.isdir(base_dir):
            return []

        entries = os.listdir(base_dir)
        for entry in entries:
            full_path = os.path.join(base_dir, entry)
            # Only include directories
            if not os.path.isdir(full_path):
                continue
            # Apply filter prefix if present
            if filter_prefix and not entry.startswith(filter_prefix):
                continue
            # Prepend directory prefix to result
            result_path = dir_prefix + entry
            directories.append(result_path)
    except PermissionError as e:
        debug(f"Permission denied: {e}")
        return []
    except OSError as e:
        debug(f"Error listing directories: {e}")
        return []

    return sorted(directories)


def _handle_flag_completion(
    context: ParserContext,
    flag_name: str,
    collection,
    incomplete: str = "",
) -> bool:
    """
    Handle completion for a flag that takes a value.

    Args:
        context: The parser context
        flag_name: The flag name (e.g., '--color')
        collection: The invoke collection
        incomplete: The incomplete value typed by user

    Returns:
        True if choices were printed, False otherwise
    """
    flag = context.flags[flag_name]
    if not flag.takes_value:
        # Boolean flags, print task names
        debug("Found, takes no value, printing task names")
        print_task_names(collection)
        return False

    # Extract the argument name from the flag object's canonical name
    # (e.g., flag.name is "search-root" regardless of whether -r or --search-root was used)
    arg_name = flag.name.replace("-", "_")

    # Special handling for search-root: complete with directories
    if arg_name == "search_root":
        debug(f"Completing search-root with directories, incomplete={incomplete!r}")
        directories = _get_directory_completions(incomplete)
        if directories:
            for directory in directories:
                print(directory)
            return True
        # Even if no directories found, we handled it (don't fall back)
        return True

    # Try to get choices for this flag
    task_name = context.name

    if task_name:
        choices = get_choices_for_argument(collection, task_name, arg_name, incomplete)
        if choices:
            debug(f"Found choices for {arg_name}: {choices}")
            for choice in choices:
                print(choice)
            return True

    # No choices found, let shell handle it (file completion)
    debug("Found, and it takes a value, so no completion")
    return False


def _try_complete_flag_value(
    tokens: List[str],
    completing_new_token: bool,
    initial_context: ParserContext,
    collection,
) -> bool:
    """
    Try to complete a value for a flag that takes a value.

    Args:
        tokens: The tokenized invocation
        completing_new_token: Whether we're completing a new token (trailing space)
        initial_context: The core context with flag definitions
        collection: The invoke collection

    Returns:
        True if completion was handled, False otherwise
    """
    if len(tokens) < 2:
        return False

    prev_token = tokens[-2] if not completing_new_token else tokens[-1]
    if not prev_token.startswith("-"):
        return False

    # Try to find the flag in initial_context (core args)
    if prev_token not in initial_context.flags:
        return False

    flag = initial_context.flags[prev_token]
    if not flag.takes_value:
        return False

    # We're completing a value for this flag
    incomplete = tokens[-1] if not completing_new_token else ""
    debug(f"Completing value for flag {prev_token}, incomplete={incomplete!r}")
    return _handle_flag_completion(initial_context, prev_token, collection, incomplete)


def _get_positional_arg_index(context: ParserContext, tokens: List[str]) -> int:
    """
    Determine which positional argument we're completing based on tokens.

    Counts non-flag tokens after the task name to determine position.

    Args:
        context: The parser context for the task
        tokens: The tokenized invocation

    Returns:
        Index of the positional argument being completed (0-based), or -1 if not applicable
    """
    if not context.name:
        return -1

    # Find where the task name is in tokens
    task_name = context.name
    task_idx = -1
    for i, token in enumerate(tokens):
        if token == task_name or token.replace("-", "_") == task_name.replace("-", "_"):
            task_idx = i
            break

    if task_idx == -1:
        return -1

    # Count positional values (non-flag tokens after task name)
    positional_count = 0
    i = task_idx + 1
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("-"):
            # It's a flag, check if it takes a value
            flag_name = token
            if flag_name in context.flags:
                flag = context.flags[flag_name]
                if flag.takes_value and i + 1 < len(tokens):
                    # Skip the flag's value
                    i += 1
        else:
            # It's a positional value
            positional_count += 1
        i += 1

    return positional_count


def _handle_positional_completion(
    context: ParserContext,
    collection,
    positional_index: int,
    incomplete: str = "",
) -> tuple[bool, bool]:
    """
    Handle completion for positional arguments.

    Args:
        context: The parser context
        collection: The invoke collection
        positional_index: Which positional argument we're completing (0-based)
        incomplete: The incomplete value typed by user

    Returns:
        Tuple of (handled, should_suppress_fallback):
        - handled: True if choices were printed
        - should_suppress_fallback: True if we're in a positional arg context
          and should NOT fall back to task name completion
    """
    task_name = context.name
    if not task_name:
        return False, False

    # Get positional args from the context
    positional_args = context.positional_args
    if positional_index >= len(positional_args):
        debug(
            f"Positional index {positional_index} out of range, allow task completion"
        )
        return False, False

    arg = positional_args[positional_index]
    arg_name: str = arg.name or ""

    debug(f"Completing positional arg {positional_index}: {arg_name}")

    # Try to get choices for this argument
    choices = get_choices_for_argument(collection, task_name, arg_name, incomplete)
    if choices:
        debug(f"Found choices for {arg_name}: {choices[:10]}...")
        for choice in choices:
            print(choice)
        return True, True

    # No choices available, but we're still within positional args range
    # Suppress fallback to task names - user needs to provide a value
    debug(f"No completion for positional arg {arg_name}, suppressing task completion")
    return False, True


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
    argument values for parameters with defined choices, including positional arguments.
    """
    # Strip out program name
    invocation = _strip_program_name(names, core.remainder)
    debug("Completing for invocation: {!r}".format(invocation))

    # Check if invocation ends with space (user wants to complete next token)
    completing_new_token = invocation.rstrip() != invocation

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
            _handle_flag_completion(context, tail, collection, incomplete="")
    # If not a flag, check if we're completing a flag value, positional args, or task names
    else:
        # Check if the previous token is a flag that takes a value
        if _try_complete_flag_value(
            tokens, completing_new_token, initial_context, collection
        ):
            raise Exit

        # Try to parse to get the current context
        contexts: List[ParserContext] = []
        try:
            debug("Parsing tokens for positional completion: {!r}".format(tokens))
            contexts = parser.parse_argv(tokens)
        except ParseError as e:
            debug(
                "Got parser error ({!r}), grabbing last-seen context {!r}".format(
                    e, e.context
                )
            )
            contexts = [e.context] if e.context is not None else []

        # Check if we have a task context (not just core context)
        if contexts and contexts[-1] and contexts[-1].name:
            context = contexts[-1]
            debug(f"In task context: {context.name}")

            # Determine which positional argument we're completing
            positional_index = _get_positional_arg_index(context, tokens)
            debug(
                f"Positional index: {positional_index}, completing_new_token: {completing_new_token}"
            )

            # Check if the last token is a partial value for completion
            incomplete = ""
            if completing_new_token:
                # User typed space after last token, completing fresh
                # positional_index is already correct
                incomplete = ""
            elif tokens:
                last_token = tokens[-1]
                # If last token is the task name, we're starting fresh
                if last_token != context.name and not last_token.startswith("-"):
                    incomplete = last_token
                    # Adjust index since we're completing the current token
                    positional_index = max(0, positional_index - 1)

            # Try to complete positional argument
            handled, suppress_fallback = _handle_positional_completion(
                context, collection, positional_index, incomplete
            )
            if handled or suppress_fallback:
                # Either we printed completions, or we're in a positional arg
                # that has no completion (like 'value') - don't show task names
                raise Exit

        # Fall back to task name completion
        debug("Last token isn't flag-like, just printing task names")
        print_task_names(collection)

    raise Exit
