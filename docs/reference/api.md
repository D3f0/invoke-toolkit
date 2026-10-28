# Toolkit API reference

This maintained reference summarizes the Toolkit-specific public surface. It is not a generated copy of every inherited method. For ordinary task options, collections, contexts, runners, Results and exceptions, use [Invoke's API reference](https://docs.pyinvoke.org/en/latest/api/index.html). Feature guides supply complete runnable examples and current constraints.

## Import map

| Import | Actual object |
| --- | --- |
| `from invoke_toolkit import Collection` | `invoke_toolkit.collections.ToolkitCollection` |
| `from invoke_toolkit import Config` | `invoke_toolkit.config.ToolkitConfig` |
| `from invoke_toolkit import Context` | `invoke_toolkit.context.ToolkitContext` |
| `from invoke_toolkit import task, call` | Toolkit decorators/call factory |
| `from invoke_toolkit.program import ToolkitProgram` | Toolkit program class |
| `from invoke_toolkit.executor import ToolkitExecutor` | Toolkit executor class |
| `from invoke_toolkit.tasks import ToolkitTask` | Task subclass with Field-aware parsing |
| `from invoke_toolkit import Program, Executor, Task, Call, Argument` | **Upstream Invoke classes**, not Toolkit aliases |
| `from invoke_toolkit import ToolkitArgument` | Toolkit parser argument subclass |

Root exports also include `Field`, `FieldResolutionRequest`, `FieldResolver`, `CacheConfig`, `cached`, `cache_stats`, `clear_task_cache`, all six path factories, `script`, `global_context`, `run` and `sudo`. `ConfigSchema`/`config_schema` and schema registry helpers are imported from `invoke_toolkit.config`, not the root. Inherited Invoke classes/exceptions re-exported at the root retain upstream semantics.

## Tasks and calls

### task

Supports both `@task` and `@task(...)`. Current keyword parameters and defaults:

| Parameter | Default |
| --- | --- |
| `name` | `None` |
| `default` | `False` |
| `aliases`, `positional`, `optional`, `iterable`, `incrementable` | `None` |
| `bool_flags` | `()` |
| `autoprint` | `False` |
| `help`, `pre`, `post` | `None` |
| `klass` | `ToolkitTask` |
| `proctitle` | `None` |
| `cache` | `None` |

Toolkit adds Enum/Literal validation, Path conversion, `Annotated` help/completion, Fields, result caching, process titles and coroutine-aware wrappers. Explicit `help` entries win over annotation help. Self-referential aliases warn and are dropped. Runtime objects are Task instances despite preserved callable typing; do not infer a plain function result from the type-preserving decorator annotation.

`autoprint=True` displays return values only for directly requested executor calls, not automatically every pre/post call. Strings and Paths use normal printing; other objects use the Toolkit Rich stdout console. It is not a universal JSON result format.

See [typed arguments](../guides/typed-arguments.md), [Fields](../guides/fields.md), [caching](../guides/caching.md), [async](../guides/async.md) and [execution](../guides/execution.md). Origins: [#38](https://github.com/D3f0/invoke-toolkit/pull/38), [#41](https://github.com/D3f0/invoke-toolkit/pull/41), [#36](https://github.com/D3f0/invoke-toolkit/pull/36), [#50](https://github.com/D3f0/invoke-toolkit/pull/50), [#51](https://github.com/D3f0/invoke-toolkit/pull/51), [#121](https://github.com/D3f0/invoke-toolkit/pull/121), [#128](https://github.com/D3f0/invoke-toolkit/pull/128), [#116](https://github.com/D3f0/invoke-toolkit/pull/116).

### call and ToolkitCall

`call(task_, *args, **kwargs) -> ToolkitCall` supplies arguments for a dependency using Invoke's Call model. `ToolkitCall.make_context(config, core_parse_result=None) -> Context` preserves upstream parser remainder text. `ctx.remainder` is inherited Invoke behavior, not sanitized argv. Origin: [#114](https://github.com/D3f0/invoke-toolkit/pull/114).

## Collections

`Collection(*args, **kwargs)` inherits Invoke's constructor for a name, tasks and subcollections. Standard `add_task`, `add_collection`, namespace lookup, aliases/defaults and `configuration(taskpath=None)` remain [Invoke APIs](https://docs.pyinvoke.org/en/latest/api/collection.html).

| Toolkit method | Contract |
| --- | --- |
| `add_collections_from_namespace(namespace: str)` | Import submodules as named subcollections |
| `add_flat_tasks_from_namespace(namespace: str) -> None` | Import submodule tasks directly into this collection |
| `load_local_tasks(search_path: str | Path | None = None) -> None` | Load `local_tasks.py` into `local`; default search is current directory |
| `load_directory(directory: str | Path) -> None` | Add a directory to the Python import path, not task discovery |
| `configure(mapping=None, *, schema=None, **kwargs) -> None` | Apply a ConfigSchema class/instance's values, then deep-merge mapping overrides; upstream `options=` keyword is accepted |
| `Collection.from_package(package_path: str, into: Collection) -> Collection` | Populate an existing collection with cleaned module subcollections and module config dictionaries; register module `config_schema` classes |
| `Collection.from_module(module, name=None, config=None, loaded_from=None, auto_dash_names=None)` | Invoke-compatible factory returning a Toolkit collection |

`load_plugins()` currently has no implementation; use namespace discovery or installed collection entry points. Namespace helpers import code and can encounter name collisions. Collection names do not automatically wrap schema/config fields at the root. See [composition and local precedence](../guides/collections.md), [schemas](../guides/configuration.md#attrs-and-cattrs-schemas) and [plugin discovery](../guides/plugins.md).

Origins: [#8](https://github.com/D3f0/invoke-toolkit/pull/8), [#21](https://github.com/D3f0/invoke-toolkit/pull/21), [#31](https://github.com/D3f0/invoke-toolkit/pull/31), [#90](https://github.com/D3f0/invoke-toolkit/pull/90), [#123](https://github.com/D3f0/invoke-toolkit/pull/123), [#133](https://github.com/D3f0/invoke-toolkit/pull/133).

## Context

`Context(config: Config | None = None, remainder: str = "")` extends [Invoke Context](https://docs.pyinvoke.org/en/latest/api/context.html).

| Toolkit member | Contract |
| --- | --- |
| `run(command: str, **kwargs) -> Result | Awaitable[Result]` | Blocking in sync tasks; native coroutine path inside Toolkit-dispatched async task unless `asynchronous` requested |
| `await run_async(command: str, **kwargs) -> Result` | Noninteractive native asyncio shell execution; buffered output |
| `gather() -> AsyncGatherScope` | Explicit concurrent awaitable scope |
| `print`, `print_err` | Bound Rich print functions to stdout and stderr respectively |
| `console` | Shared Rich stderr console |
| `status(message, *, spinner="dots", spinner_style="status.spinner", speed=1.0, refresh_per_second=12.5)` | Status context manager, with config-aware disabled/live-output modes |
| `status_update(status=None, *, spinner=None, spinner_style=None, speed=None)` | Update the active status |
| `status_stop()` | Stop the active status |
| `rich_exit(message="Exited", exit_code=1)` | Log with Rich and raise SystemExit |
| `inspect(obj, *, title=None, help_=False, methods=False, docs=True, private=False, dunder=False, sort=True, all_=False, value=True, stream="err")` | Rich object inspection; stream is `out` or `err` |
| `redact(streams: str | dict[str, list[str]], patterns: list[str] | None = None)` | Best-effort selected output redaction context manager |
| `proctitle(title: str)` | Set and restore process/tmux title |
| `get_config_value(path, default=not_supplied, exit_message=None, exit_code=None, required=False)` | Dot-path config helper; `not_supplied` describes its sentinel, not a public argument value |
| `get_schema(schema_cls, path=None)` | Typed config snapshot; missing path uses schema defaults |

`status`, `status_update`, `print` and `print_err` are exposed as properties returning callables. Output is not inherently machine-readable; use `json.dumps` for an explicit task contract. Redaction is not secret isolation and has shared-state/exception restoration limitations. `run_async` does not provide PTY, stdin, watchers, sudo, streaming or synchronous-runner redaction parity. See [Rich output](../humans/rich-output.md), [async restrictions](../guides/async.md#native-subprocess-limits) and [execution safety](../guides/execution.md).

`AsyncGatherScope` lives in `invoke_toolkit.context.async_tools`. Submit awaitables with `scope(awaitable)` inside `async with scope`; `.results` is a tuple after successful exit. Work starts on submission; unfinished work is cancelled on failure. Origin: [#121](https://github.com/D3f0/invoke-toolkit/pull/121), repairs [#127](https://github.com/D3f0/invoke-toolkit/pull/127).

## Configuration and schemas

`Config` retains [Invoke Config](https://docs.pyinvoke.org/en/latest/api/config.html) constructor/loading methods. Subclass definition accepts `prefix=None`, `file_prefix=None`, `env_prefix=None`, `extra_defaults=None`. `global_defaults()` adds Toolkit's synchronous runner, status/completion and fuzzy-finder settings.

| Public API | Contract |
| --- | --- |
| `Config.as_schema(schema_cls, path=None)` | Convert an existing config section/root to a ConfigSchema instance; missing path raises KeyError |
| `Config.update_from(schema, path=None)` | Apply schema values to an existing in-memory section/root; does not persist files |
| `get_config_value(ctx, path, default=not_supplied, exit_message=None, exit_code=None, required=False)` | Standalone equivalent of context helper |
| `ConfigSchema.from_dict(data)` | cattrs structure with attrs defaults for omitted fields |
| `schema.to_dict()` | cattrs unstructure |
| `ConfigSchema.get_converter()` | Shared converter for custom hooks |
| `@config_schema` or `@config_schema(collection_name, description=None)` | Apply attrs and schema metadata/methods; register by collection name |
| `register_schema(collection_name, schema)` | Register a schema class |
| `get_schema(collection_name)` | Get registered class or None |
| `get_all_schemas()` | Return registry dictionary snapshot |
| `get_schema_info(schema)` | Return display-oriented field/type/default metadata |
| `get_field_type(path)` | Get registered type for a dot path or None |
| `validate_value(path, value)` | Return `(valid: bool, error: str | None)` |
| `clear_registry()` | Clear process-local registrations, primarily for test isolation |

Use `ConfigSchema` inheritance for APIs requiring that subclass; `@config_schema` alone adds helpers but does not change inheritance. Registry keys and configuration placement are separate decisions. Built-in file editing tasks are in the [CLI reference](cli.md), with [configuration validation/format limits](../guides/configuration.md). Origins: [#11](https://github.com/D3f0/invoke-toolkit/pull/11), [#52](https://github.com/D3f0/invoke-toolkit/pull/52), [#90](https://github.com/D3f0/invoke-toolkit/pull/90), [#93](https://github.com/D3f0/invoke-toolkit/pull/93), [#94](https://github.com/D3f0/invoke-toolkit/pull/94).

## Path annotations

Import all factories from `invoke_toolkit`; they return `Annotated` types. Their supported signatures are:

- `FilePath(*, exists=False, file_okay=True, dir_okay=True)` and `FilePathStr` with the same parameters.
- `FilePattern(pattern: str, *, exists=False)` and `FilePatternStr` with the same parameters.
- `DirPath(*, exists=False)` and `DirPathStr` with the same parameters.

The non-`Str` forms receive `Path`, the `Str` forms receive strings. Glob/type filters guide completion; `exists=True` enables runtime existence/type checks. Plain `Path` converts explicit strings but does not imply all completion/validation constraints. See [typed paths](../guides/typed-arguments.md#path-annotations-and-completion-filters). Origin: [#41](https://github.com/D3f0/invoke-toolkit/pull/41).

## Fields

`Field(default=UNSET, default_factory=UNSET, resolver=None, cleanup="pipeline")` is the runtime marker; `UNSET` here describes omitted arguments, not a value you need to import. `Field()` is required, unlike `Field(default=None)`.

- `field.required` reports whether it lacks a default/factory.
- A required template can be bound as `field(default=...)` or `field(default_factory=..., cleanup=None)`. It preserves the resolver and inherits cleanup unless overridden.
- `field.create_temporary_file(request, value: str) -> Path` is the materialization hook for resolver text with a Path annotation.
- `FieldResolutionRequest(parameter: str, reference: str, annotation)` is a frozen request record.
- `FieldResolver` is a callable protocol: `(ctx, requests: Sequence[FieldResolutionRequest]) -> Mapping[str, str]`.

Local batches use scheme plus callable identity. Results must contain exactly the requested names, with string values. Exact Path-base fields turn that text into managed files; explicit caller paths remain caller-owned. Bool/incrementable/iterable parameters do not support Field defaults. See [precedence and lifetime](../guides/fields.md).

Installed compatibility providers use `invoke_toolkit.field_resolver`; providers are not task collections. `reset_field_resolver_cache()` in `invoke_toolkit.field_resolvers` clears cached entry-point discovery/warning state for controlled process/test lifecycle use. It does not clean files or resolve values. Origin: [#128](https://github.com/D3f0/invoke-toolkit/pull/128).

## Caching

- `CacheConfig(enabled=True, ttl=None, key_prefix="", ignore_args=[])`: task-result cache options.
- `clear_task_cache(task_name: str | None = None) -> int`: clear all/current-prefix task keys; hashed-key limitations apply.
- `cache_stats() -> dict[str, Any]`: availability and disk statistics.
- `cached(ttl: float = 300.0, maxsize: int | None = None)`: completion callback decorator; `maxsize` is bytes.
- Cached completion functions expose `cache_clear()` and `cache_info()`.

Task and completion keys do not automatically fingerprint source/config/environment. Requires optional diskcache for persistence. See [cache ownership and correctness](../guides/caching.md). Origins: [#51](https://github.com/D3f0/invoke-toolkit/pull/51), [#76](https://github.com/D3f0/invoke-toolkit/pull/76).

## Programs, executors and portable scripts

`ToolkitProgram(version=None, namespace=None, name=None, binary=None, loader_class=None, executor_class=ToolkitExecutor, config_class=Config, binary_names=None)` integrates Toolkit parsing, local/plugin loading and execution. `.run(argv: list[str] | None = None, exit=True) -> None` executes CLI parsing/dispatch; `exit=False` is intended mainly for testing and is not a general exception-propagating embedding API. Async CLI dispatch owns an `asyncio.run()` loop.

A complete custom application, saved as `app.py` in an installed environment:

```python
from invoke_toolkit import Collection, Config, Context, task
from invoke_toolkit.program import ToolkitProgram


class AppConfig(Config, prefix="myapp", extra_defaults={"app": {"label": "custom"}}):
    """Application defaults and file prefix."""


@task
def hello(ctx: Context) -> None:
    print(ctx.get_config_value("app.label"))


def main() -> None:
    namespace = Collection(hello)
    ToolkitProgram(namespace=namespace, config_class=AppConfig, name="My application").run()


if __name__ == "__main__":
    main()
```

```bash
python app.py hello
python app.py --list
```

Providing `namespace` is explicit collection bootstrap: normal filesystem/plugin discovery is not automatically invoked for that namespace. Project configuration still loads from the current directory. For custom collection composition, populate `namespace` with [Collection helpers](../guides/collections.md) before supplying it.

`ToolkitExecutor(collection, config=None, core=None)` defaults to Toolkit Config and an empty upstream `ParseResult`. `execute(*tasks)` handles synchronous calls; `await execute_async(*tasks)` awaits coroutine results in the same sequential graph. Task inputs are names, `(name, kwargs)` tuples or parsed `ParserContext` objects; results map task objects to their returned values. In an existing event loop, call `execute_async` directly rather than `ToolkitProgram.run`.

`script(argv=None, exit=True, config_prefix=None) -> None` collects decorated tasks from its caller's namespace and runs a Toolkit program. Guard it with `if __name__ == "__main__"` and declare dependencies for a [PEP 723 script](../pep723/index.md). Import-time guards do not sandbox Python imports or dependency installation. Origins: [#11](https://github.com/D3f0/invoke-toolkit/pull/11), [#17](https://github.com/D3f0/invoke-toolkit/pull/17), [#104](https://github.com/D3f0/invoke-toolkit/pull/104), async [#121](https://github.com/D3f0/invoke-toolkit/pull/121), compatibility [#114](https://github.com/D3f0/invoke-toolkit/pull/114).

`ToolkitArgument` extends upstream Argument's constructor with `complete=None`; the callback accepts context/incomplete text. `.was_explicitly_set` reflects parser `got_value`. Most task authors should use `Annotated` rather than construct arguments themselves ([#41](https://github.com/D3f0/invoke-toolkit/pull/41), [#128](https://github.com/D3f0/invoke-toolkit/pull/128)).

## Global helpers and output utilities

`global_context() -> Context` lazily creates a singleton, with non-TTY stdin disabled. Root `run(command, **kwargs)` and `sudo(command, **kwargs)` delegate to it. They are for REPL/top-level convenience; tasks should use their supplied `ctx` for loaded config and pipeline lifecycle. The global helper does not promise automatic project config loading. Origin: [#13](https://github.com/D3f0/invoke-toolkit/pull/13).

`invoke_toolkit.output.get_console(stream="err")` returns a shared `SecretRedactorConsole` for `out`, `err` or `log`; `log` also writes stderr. `SecretRedactorConsole(secret_patterns=None, substitution="${}", ...)` extends Rich Console; `.secret_patterns` selects environment names and `.redact(text)` filters a string. These consoles are shared output devices, not task-local secret containers. See [redaction limits](../guides/execution.md#output-redaction-is-not-secret-isolation) ([#30](https://github.com/D3f0/invoke-toolkit/pull/30)).

`invoke_toolkit.utils.fzf` exposes `is_fzf_available()`, `select(ctx, choices, prompt="Select an option", multi=False, preview=None, preview_window="right:50%", height="40%", reverse=True, use_fallback=True, **kwargs)` and `select_from_command(ctx, command, ...)` with the same selection options. Results are a string, list of strings for multiselect, or None. Its Rich fallback is reduced functionality, not fzf feature parity; command/preview shell inputs must be trusted. See [interactive selection](../humans/interactive-selection.md). Origins: [#80](https://github.com/D3f0/invoke-toolkit/pull/80), [#81](https://github.com/D3f0/invoke-toolkit/pull/81), [#82](https://github.com/D3f0/invoke-toolkit/pull/82), [#83](https://github.com/D3f0/invoke-toolkit/pull/83).

## Testing support

`invoke_toolkit.testing.TestingToolkitProgram` uses a Toolkit config with stdin disabled and defaults `.run(..., exit=False)` for tests. Upstream `MockContext` and Result/exception types remain available from the root. For assertions around task behavior, prefer the real execution surface relevant to your application rather than treating help/list imports as pure discovery.

Built-in `create`, `config`, `shell` and uv `plugin` tasks are CLI surfaces documented in [CLI reference](cli.md) and their guides. The `dist` module has no actionable distribution task; no binary/download packaging API is promised.
