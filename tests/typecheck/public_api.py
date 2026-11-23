"""Consumer imports of the supported package-root API."""

# ruff: noqa: F401 -- importing every public name is the typing contract.

from typing_extensions import assert_type

from invoke_toolkit import (
    AmbiguousEnvVar,
    Argument,
    AuthFailure,
    CacheConfig,
    Call,
    Collection,
    CollectionNotFound,
    CommandTimedOut,
    Config,
    Context,
    DirPath,
    DirPathStr,
    Executor,
    Exit,
    FailingResponder,
    Failure,
    Field,
    FieldResolutionRequest,
    FieldResolver,
    FilePath,
    FilePathStr,
    FilePattern,
    FilePatternStr,
    FilesystemLoader,
    Local,
    MockContext,
    ParseError,
    ParseResult,
    Parser,
    ParserContext,
    PlatformError,
    Program,
    Promise,
    Responder,
    ResponseNotAccepted,
    Result,
    Runner,
    StreamWatcher,
    SubprocessPipeError,
    Task,
    ThreadException,
    ToolkitArgument,
    UncastableEnvVar,
    UnexpectedExit,
    UnknownFileType,
    UnpicklableConfigMember,
    WatcherError,
    __version__,
    cache_stats,
    cached,
    call,
    clear_task_cache,
    global_context,
    pty_size,
    run,
    script,
    sudo,
    task,
)


@task
def greet(ctx: Context, name: str = "world") -> str:
    return f"{ctx.config.get('greeting', 'Hello')}, {name}!"


assert_type(Config(), Config)
assert_type(Context(config=Config()), Context)
assert_type(Collection(), Collection)
assert_type(__version__, str)
