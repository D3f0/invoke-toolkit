"""
Custom completion support for Enum and Literal parameter choices.

This module extends invoke's completion system to support completing
argument values for Enum and Literal parameters.
"""

import re
import shlex
from typing import List

from invoke.completion.complete import (
    debug,
    print_task_names,
)
from invoke.exceptions import Exit, ParseError
from invoke.parser import Parser, ParserContext

from invoke_toolkit.tasks.tasks import (
    _extract_enum_params,
    _extract_literal_params,
)


def get_choices_for_argument(collection, context_name: str, arg_name: str) -> List[str]:
    """
    Get available choices for an argument in a task.

    Args:
        collection: The invoke collection
        context_name: The task name
        arg_name: The argument name (without dashes)

    Returns:
        List of choice strings, or empty list if no choices defined
    """
    choices = []

    # Try to get the task from the collection
    try:
        task = collection[context_name]
    except KeyError:
        return choices

    # Get the wrapped function if available
    func = task.body
    if hasattr(func, "__wrapped__"):
        func = func.__wrapped__

    # Extract enum parameters
    enum_params = _extract_enum_params(func)
    if arg_name in enum_params:
        enum_class = enum_params[arg_name]
        choices = [str(member.value) for member in enum_class]
        return choices

    # Extract literal parameters
    literal_params = _extract_literal_params(func)
    if arg_name in literal_params:
        literal_values = literal_params[arg_name]
        choices = [str(v) for v in literal_values]
        return choices

    return choices


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
        choices = get_choices_for_argument(collection, task_name, arg_name)
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
