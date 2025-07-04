"""
TBD if this needs to be called tasks to keep consistency
with invoke and use another entry point to install tasks.
"""

from invoke.task import Task
from typing import Any, Callable, Type, TypeVar, cast, overload, Union
from functools import wraps, update_wrapper

# Define a TypeVar for the callable
T = TypeVar("T", bound=Callable)


@overload
def task(func: T) -> Task[T]: ...


@overload
def task(
    *args: Any,
    name: str = None,
    aliases: list[str] = None,
    positional: list[str] = None,
    optional: list[str] = None,
    default: bool = False,
    auto_shortflags: bool = True,
    help: dict[str, str] = None,
    pre: list = None,
    post: list = None,
    autoprint: bool = False,
    iterable: list[str] = None,
    incrementable: list[str] = None,
    klass: Type[Task] = Task,
) -> Callable[[T], Task[T]]: ...


def task(*args: Any, **kwargs: Any) -> Union[Task[T], Callable[[T], Task[T]]]:
    """
    Marks wrapped callable object as a valid Invoke task.

    May be called without any parentheses if no extra options need to be
    specified. Otherwise, the following keyword arguments are allowed in the
    parenthese'd form:

    * ``name``: Default name to use when binding to a `.Collection`. Useful for
      avoiding Python namespace issues (i.e. when the desired CLI level name
      can't or shouldn't be used as the Python level name.)
    * ``aliases``: Specify one or more aliases for this task, allowing it to be
      invoked as multiple different names. For example, a task named ``mytask``
      with a simple ``@task`` wrapper may only be invoked as ``"mytask"``.
      Changing the decorator to be ``@task(aliases=['myothertask'])`` allows
      invocation as ``"mytask"`` *or* ``"myothertask"``.
    * ``positional``: Iterable overriding the parser's automatic "args with no
      default value are considered positional" behavior. If a list of arg
      names, no args besides those named in this iterable will be considered
      positional. (This means that an empty list will force all arguments to be
      given as explicit flags.)
    * ``optional``: Iterable of argument names, declaring those args to
      have :ref:`optional values <optional-values>`. Such arguments may be
      given as value-taking options (e.g. ``--my-arg=myvalue``, wherein the
      task is given ``"myvalue"``) or as Boolean flags (``--my-arg``, resulting
      in ``True``).
    * ``iterable``: Iterable of argument names, declaring them to :ref:`build
      iterable values <iterable-flag-values>`.
    * ``incrementable``: Iterable of argument names, declaring them to
      :ref:`increment their values <incrementable-flag-values>`.
    * ``default``: Boolean option specifying whether this task should be its
      collection's default task (i.e. called if the collection's own name is
      given.)
    * ``auto_shortflags``: Whether or not to automatically create short
      flags from task options; defaults to True.
    * ``help``: Dict mapping argument names to their help strings. Will be
      displayed in ``--help`` output. For arguments containing underscores
      (which are transformed into dashes on the CLI by default), either the
      dashed or underscored version may be supplied here.
    * ``pre``, ``post``: Lists of task objects to execute prior to, or after,
      the wrapped task whenever it is executed.
    * ``autoprint``: Boolean determining whether to automatically print this
      task's return value to standard output when invoked directly via the CLI.
      Defaults to False.
    * ``klass``: Class to instantiate/return. Defaults to `.Task`.

    If any non-keyword arguments are given, they are taken as the value of the
    ``pre`` kwarg for convenience's sake. (It is an error to give both
    ``*args`` and ``pre`` at the same time.)

    .. versionadded:: 1.0
    .. versionchanged:: 1.1
        Added the ``klass`` keyword argument.
    """
    klass: Type[Task] = kwargs.pop("klass", Task)
    # @task -- no options were (probably) given.
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        return cast(Task[T], klass(args[0], **kwargs))
    # @task(pre, tasks, here)
    if args:
        if "pre" in kwargs:
            raise TypeError("May not give *args and 'pre' kwarg simultaneously!")
        kwargs["pre"] = args

    def inner(body: T) -> Task[T]:
        _task = klass(body, **kwargs)
        # Preserve the original function's metadata
        update_wrapper(_task, body)
        return cast(Task[T], _task)

    return inner
