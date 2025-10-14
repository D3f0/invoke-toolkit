"""
Custom executor class to for Syntax highlighted output
"""

from typing import Any, Dict, Tuple, Union
from invoke.executor import Executor
from invoke.parser import ParserContext
from invoke.util import debug
from invoke.tasks import Task
from invoke.runners import Result
from invoke_toolkit.output import get_console


class InvokeToolkitExecutor(Executor):
    """Task execution"""

    def execute(
        self, *tasks: Union[str, Tuple[str, Dict[str, Any]], ParserContext]
    ) -> Dict["Task", "Result"]:
        """
        Execute one or more ``tasks`` in sequence.

        :param tasks:
            An all-purpose iterable of "tasks to execute", each member of which
            may take one of the following forms:

            **A string** naming a task from the Executor's `.Collection`. This
            name may contain dotted syntax appropriate for calling namespaced
            tasks, e.g. ``subcollection.taskname``. Such tasks are executed
            without arguments.

            **A two-tuple** whose first element is a task name string (as
            above) and whose second element is a dict suitable for use as
            ``**kwargs`` when calling the named task. E.g.::

                [
                    ('task1', {}),
                    ('task2', {'arg1': 'val1'}),
                    ...
                ]

            is equivalent, roughly, to::

                task1()
                task2(arg1='val1')

            **A `.ParserContext`** instance, whose ``.name`` attribute is used
            as the task name and whose ``.as_kwargs`` attribute is used as the
            task kwargs (again following the above specifications).

            .. note::
                When called without any arguments at all (i.e. when ``*tasks``
                is empty), the default task from ``self.collection`` is used
                instead, if defined.

        :returns:
            A dict mapping task objects to their return values.

            This dict may include pre- and post-tasks if any were executed. For
            example, in a collection with a ``build`` task depending on another
            task named ``setup``, executing ``build`` will result in a dict
            with two keys, one for ``build`` and one for ``setup``.

        .. versionadded:: 1.0
        """
        # Normalize input
        debug("Examining top level tasks {!r}".format(list(tasks)))  # pylint: disable=W1202
        calls = self.normalize(tasks)
        debug("Tasks (now Calls) with kwargs: {!r}".format(calls))  # pylint: disable=W1202
        # Obtain copy of directly-given tasks since they should sometimes
        # behave differently
        direct = list(calls)
        # Expand pre/post tasks
        # TODO: may make sense to bundle expansion & deduping now eh?
        expanded = self.expand_calls(calls)
        # Get some good value for dedupe option, even if config doesn't have
        # the tree we expect. (This is a concession to testing.)
        try:
            dedupe = self.config.tasks.dedupe
        except AttributeError:
            dedupe = True
        # Dedupe across entire run now that we know about all calls in order
        calls = self.dedupe(expanded) if dedupe else expanded
        # Execute
        results = {}
        # TODO: maybe clone initial config here? Probably not necessary,
        # especially given Executor is not designed to execute() >1 time at the
        # moment...
        for call in calls:
            autoprint = call in direct and call.autoprint
            debug("Executing {!r}".format(call))  # pylint: disable=W1202
            # Hand in reference to our config, which will preserve user
            # modifications across the lifetime of the session.
            config = self.config
            # But make sure we reset its task-sensitive levels each time
            # (collection & shell env)
            # TODO: load_collection needs to be skipped if task is anonymous
            # (Fabric 2 or other subclassing libs only)
            collection_config = self.collection.configuration(call.called_as)
            config.load_collection(collection_config)
            config.load_shell_env()
            debug("Finished loading collection & shell env configs")
            # Get final context from the Call (which will know how to generate
            # an appropriate one; e.g. subclasses might use extra data from
            # being parameterized), handing in this config for use there.
            context = call.make_context(config)
            args = (context, *call.args)
            result = call.task(*args, **call.kwargs)
            if autoprint:
                get_console().print(result)
                # print(result)
            # TODO: handle the non-dedupe case / the same-task-different-args
            # case, wherein one task obj maps to >1 result.
            results[call.task] = result
        return results
