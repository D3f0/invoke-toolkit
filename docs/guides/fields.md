# Deferred task Fields

`Field` adds execution-time defaults to task parameters. Use it for values that depend on loaded configuration, a callback or a URI resolver. It is not a [configuration schema](configuration.md#attrs-and-cattrs-schemas) and does not make all task discovery side-effect free.

Origin: [#128](https://github.com/D3f0/invoke-toolkit/pull/128).

## Static, required and factory defaults

Save this complete `tasks.py` after [installation](../getting-started/installation.md):

```python
from invoke_toolkit import Collection, Context, Field, task


def default_label(ctx: Context) -> str:
    return ctx.get_config_value("app.label", default="local")


@task
def describe(
    ctx: Context,
    label: str = Field(default_factory=default_label),
    style: str = Field(default="brief"),
) -> None:
    """Print execution-time defaults."""
    print(f"label={label}, style={style}")


@task
def required_label(ctx: Context, label: str = Field()) -> None:
    """Require a caller-supplied label."""
    print(label)


ns = Collection(describe, required_label)
ns.configure({"app": {"label": "project"}})
```

```bash
intk describe
intk describe --label explicit
intk required-label --label explicit
```

A factory receives the execution `Context`, not `(ctx, incomplete)` like a completion callback. `Field(default=...)` and `Field(default_factory=...)` are mutually exclusive. `Field(default=None)` is an optional default; `Field()` without either is required. Required Fields must be supplied by the caller; environment/config lookups do not fill a missing required Field.

Factories and resolvers do not execute during help, listing or shell completion. Importing `tasks.py` still executes its module-level code, and completion callbacks are independent callbacks. Keep all initialization/import work safe to repeat.

## Precedence and explicit values

Boolean, incrementable and iterable parameters do not support Field defaults in the current parser. Use ordinary task defaults for those arguments; do not promise a Field factory bypasses these restrictions.

For a non-required Field, the order is:

1. Explicit CLI, direct Python or parameterized pre-task values.
2. `INVOKE_<PARAMETER_NAME_UPPERCASE>` environment value, for example `INVOKE_LABEL`.
3. A value at the execution config's top-level parameter key, for example `ctx.config["label"]`.
4. The Field's declared default or its `default_factory(ctx)`.

A factory runs only when no higher-precedence value exists. A config value of `None` still wins. The automatic config key is the parameter name, **not** a nested path such as `app.label`; the factory above deliberately reads that path itself.

```bash
INVOKE_LABEL=environment intk describe
INVOKE_LABEL=environment intk describe --label explicit
```

Only omitted Field values enter URI resolution. An explicit `--label env://LABEL` is literal caller input and does not trigger a resolver. The same bypass applies to direct task calls and `call(task, label=...)` pre-task arguments. Enum/Literal/Path processing still applies where supported; arbitrary scalar type coercion is not promised. In particular, automatic environment values and URI resolver results are text, not automatically converted to every annotated numeric/bool type. Return a correctly typed scalar from a factory when you need one.

## Task-local batched URI resolvers

Prefer a task-local `Field(resolver=callback)` over ambient provider discovery. The callable is synchronous:

```text
resolver(ctx, requests) -> Mapping[str, str]
```

Each `FieldResolutionRequest` contains `parameter`, the full URI `reference`, and the base `annotation`. The callback must return **exactly** the requested parameter names with **string** values. No extra/missing keys, bytes, paths or arbitrary objects are accepted. Toolkit groups omitted URI fields by URI scheme and callback identity within each task invocation, then calls the callback once for each batch. Ordinary non-URI defaults do not invoke it.

The following complete `tasks.py` resolves real environment values in one batch and uses the same resolver template for a scalar and a UTF-8 file:

```python
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from invoke_toolkit import Context, Field, FieldResolutionRequest, task


def resolve_environment(
    ctx: Context,
    requests: Sequence[FieldResolutionRequest],
) -> Mapping[str, str]:
    resolved = {}
    for request in requests:
        scheme, variable = request.reference.split("://", 1)
        if scheme != "env" or not variable.isidentifier():
            raise ValueError("Expected an env://VARIABLE reference")
        resolved[request.parameter] = os.environ[variable]
    return resolved


EnvironmentField = Field(resolver=resolve_environment)


@task
def read_settings(
    ctx: Context,
    message: str = EnvironmentField(default="env://DOCS_MESSAGE"),
    settings: Path = EnvironmentField(
        default="env://DOCS_SETTINGS", cleanup="task"
    ),
) -> None:
    """Consume a scalar and a managed file without exposing secret contents."""
    print(f"Message length: {len(message)}")
    print(f"Settings lines: {len(settings.read_text(encoding='utf-8').splitlines())}")
```

```bash
DOCS_MESSAGE='Documentation example' DOCS_SETTINGS='{"enabled": true}' intk read-settings
```

No provider package or external secret-manager command is required for this environment resolver. For a real service, implement its actual API in the callback, set operation-level timeouts and do not log URI references/resolved values. If calling a CLI, pass an argument list to `subprocess.run` rather than interpolating references into a shell string; see [safe execution](execution.md#shell-strings-and-argument-lists).

`EnvironmentField` is a required resolver template; calling it with `default=` or `default_factory=` creates a bound Field. A Field that already has a default cannot be rebound with a call. Resolver failures stop task execution with provider/parameter diagnostics that omit the exception's potentially sensitive message.

## Scalar text versus managed Path files

A resolver's string passes through as scalar text. With an exact base `pathlib.Path` annotation (including `FilePath()`'s `Annotated[Path, ...]`), Toolkit instead writes the returned text to a managed UTF-8 temporary file and passes its `Path`. The string is the **file contents**, not an existing filename. `FilePathStr()` remains scalar text. Do not rely on optional Path unions receiving the same materialization behavior; use an exact Path base for managed files.

| `cleanup` | Lifetime |
| --- | --- |
| `"pipeline"` (default) | Until the executor's whole pre/main/post task invocation pipeline finishes |
| `"task"` | Until this task wrapper finishes, including failure |

The executor owns managed files, reference-counts shared paths and releases them in reverse registration order. A direct Python task call without an executor owns its own cleanup boundary, so even `pipeline` files are removed when that direct call finishes. Never return a managed Path as a durable artifact or expect cached Paths to remain usable after cleanup. Copy contents to an application-owned destination when persistence is required.

Only files **created by a resolver-backed Field** are managed. Explicit paths and Paths returned by a normal default factory remain caller-owned and are not deleted. Temporary materialization happens before path validation, so an `exists=True` file annotation can validate the managed file. A `Field` subclass may override `create_temporary_file(request, value) -> Path` for encoding/storage needs; the returned file is then Toolkit-owned and eligible for deletion.

## Installed providers

Compatibility discovery uses the `invoke_toolkit.field_resolver` entry-point group, keyed by URI scheme. Global batches are grouped by scheme; discovery is cached per process. When a Field has no local callback, Toolkit loads an installed matching provider and warns that task-local resolvers are preferred. Missing/unusable providers fail execution rather than treating the URI as resolved.

[Provider-only package creation](packages.md#resolver-only-packages) documents a full implementation. Such a package has no collection entry point and exposes no `intk` tasks; it must be installed in the consumer's environment. Neither providers nor URI defaults imply built-in support for Bitwarden, 1Password or remote HTTP fetching. The local resolver is your implementation and trust boundary.

Field materialization precedes [task caching](caching.md#task-result-cache): a cache key sees materialized arguments, and a cache hit does not skip factory/resolver work. Avoid cache keys/results containing secrets or managed temporary Paths.
