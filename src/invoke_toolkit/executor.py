"""
Custom executor class to for Syntax highlighted output
"""

import inspect
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Optional, cast

from invoke.executor import Executor
from invoke.parser import ParserContext, ParseResult
from invoke.runners import Result
from invoke.tasks import Task
from invoke.util import debug

from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.config import ToolkitConfig
from invoke_toolkit.context.async_tools import async_task_context
from invoke_toolkit.output import get_console
from invoke_toolkit.field_resolvers import FieldCleanupManager
from invoke_toolkit.tasks.tasks import ToolkitCall, ToolkitTask


class ToolkitExecutor(Executor):
    """Task execution"""

    def __init__(  # pylint: disable=super-init-not-called
        self,
        collection: "ToolkitCollection",
        config: Optional["ToolkitConfig"] = None,
        core: Optional["ParseResult"] = None,
    ) -> None:
        """
        Initialize executor with handles to necessary data structures.

        :param collection:
            A `.Collection` used to look up requested tasks (and their default
            config data, if any) by name during execution.

        :param config:
            An optional `.Config` holding configuration state. Defaults to an
            empty `.Config` if not given.

        :param core:
            An optional `.ParseResult` holding parsed core program arguments.
            Defaults to an empty `.ParseResult` if not given.

        .. versionchanged:: invoke 3.0
            ``self.core`` now defaults to ``ParseResult()`` instead of
            ``None``, matching upstream ``Executor`` behaviour and ensuring
            ``core_parse_result.remainder`` is always accessible.
        """
        self.collection = collection
        self.config = config if config is not None else ToolkitConfig()
        self.core = core if core is not None else ParseResult()

    async def execute_async(
        self, *tasks: str | tuple[str, dict[str, Any]] | ParserContext
    ) -> dict["ToolkitTask", Any]:
        """Execute task calls in order, awaiting coroutine task results."""
        calls = self.normalize(tasks)
        direct = list(calls)
        expanded = self.expand_calls(calls)
        try:
            dedupe = self.config.tasks.dedupe
        except AttributeError:
            dedupe = True
        calls = self.dedupe(expanded) if dedupe else expanded
        results: dict[ToolkitTask, Any] = {}
        cleanup = FieldCleanupManager()
        failed = False
        try:
            for call in calls:
                autoprint = call in direct and call.autoprint
                config = self.config
                collection_config = self.collection.configuration(call.called_as)
                config.load_collection(collection_config)
                config.load_shell_env()
                context = call.make_context(config, core_parse_result=self.core)
                context._field_cleanup = cleanup
                args = (context, *call.args)
                context_manager = (
                    async_task_context()
                    if inspect.iscoroutinefunction(call.task.body)
                    else nullcontext()
                )
                with context_manager:
                    result = call.task(*args, **call.kwargs)
                    if inspect.isawaitable(result):
                        result = await result
                if autoprint:
                    if isinstance(result, (str, Path)):
                        print(result)
                    else:
                        get_console("out").print(result)
                results[call.task] = result  # ty: ignore[invalid-assignment]
            return results
        except BaseException:
            failed = True
            raise
        finally:
            cleanup.close_pipeline(failed)

    def execute(
        self, *tasks: str | tuple[str, dict[str, Any]] | ParserContext
    ) -> dict["ToolkitTask", "Result"]:
        """Execute one or more tasks in sequence."""
        debug(f"Examining top level tasks {list(tasks)!r}")
        calls = self.normalize(tasks)
        direct = list(calls)
        expanded = self.expand_calls(calls)
        try:
            dedupe = self.config.tasks.dedupe
        except AttributeError:
            dedupe = True
        calls = self.dedupe(expanded) if dedupe else expanded
        results = {}
        cleanup = FieldCleanupManager()
        failed = False
        try:
            for call in calls:
                autoprint = call in direct and call.autoprint
                config = self.config
                collection_config = self.collection.configuration(call.called_as)
                config.load_collection(collection_config)
                config.load_shell_env()
                context = call.make_context(config, core_parse_result=self.core)
                context._field_cleanup = cleanup
                args = (context, *call.args)
                result = call.task(*args, **call.kwargs)
                if autoprint:
                    if isinstance(result, (str, Path)):
                        print(result)
                    else:
                        get_console("out").print(result)
                results[call.task] = result
            return results
        except BaseException:
            failed = True
            raise
        finally:
            cleanup.close_pipeline(failed)

    def normalize(
        self,
        tasks: tuple[str | tuple[str, dict[str, Any]] | ParserContext, ...],
    ) -> list["ToolkitCall"]:
        """
        Transform arbitrary task list w/ various types, into `.Call` objects.

        See docstring for `~.Executor.execute` for details.

        .. versionadded:: 1.0
        """
        calls = []
        for task in tasks:
            name: str | None
            kwargs: dict[str, Any]
            if isinstance(task, str):
                name = task
                kwargs = {}
            elif isinstance(task, ParserContext):
                name = task.name
                kwargs = task.as_kwargs
            else:
                name, kwargs = task  # type: ignore[misc]
            c = ToolkitCall(self.collection[name], kwargs=kwargs, called_as=name)
            calls.append(c)
        if not tasks and self.collection.default is not None:
            calls = [ToolkitCall(self.collection[self.collection.default])]
        return calls

    def dedupe(self, calls: list["ToolkitCall"]) -> list["ToolkitCall"]:
        """
        Deduplicate a list of `tasks <.Call>`.

        :param calls: An iterable of `.Call` objects representing tasks.

        :returns: A list of `.Call` objects.

        .. versionadded:: 1.0
        """
        deduped = []
        debug("Deduplicating tasks...")
        for call in calls:
            if call not in deduped:
                debug(f"{call!r}: no duplicates found, ok")
                deduped.append(call)
            else:
                debug(f"{call!r}: found in list already, skipping")
        return deduped

    def expand_calls(self, calls: list["ToolkitCall"]) -> list["ToolkitCall"]:
        """
        Expand a list of `.Call` objects into a near-final list of same.

        The default implementation of this method simply adds a task's
        pre/post-task list before/after the task itself, as necessary.

        Subclasses may wish to do other things in addition (or instead of) the
        above, such as multiplying the `calls <.Call>` by argument vectors or
        similar.

        .. versionadded:: 1.0
        """
        ret = []
        for call in calls:
            if isinstance(call, (list, tuple)):
                ret.extend(self.expand_calls(cast(list[ToolkitCall], call)))
                continue
            # Normalize to Call (this method is sometimes called with pre/post
            # task lists, which may contain 'raw' Task objects)
            if isinstance(call, Task):
                call = ToolkitCall(call)
            debug(f"Expanding task-call {call!r}")
            # TODO: this is where we _used_ to call Executor.config_for(call,
            # config)...
            # TODO: now we may need to preserve more info like where the call
            # came from, etc, but I feel like that shit should go _on the call
            # itself_ right???
            # TODO: we _probably_ don't even want the config in here anymore,
            # we want this to _just_ be about the recursion across pre/post
            # tasks or parameterization...?
            ret.extend(self.expand_calls(call.pre))
            ret.append(call)
            ret.extend(self.expand_calls(call.post))
        return ret
