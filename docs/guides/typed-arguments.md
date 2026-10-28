# Typed task arguments

Invoke derives CLI arguments primarily from function defaults. Toolkit adds annotation-driven choices, help, completion callbacks and path conversion while keeping Invoke's task syntax. Start with [your first task](../getting-started/quickstart.md); the examples below replace its `tasks.py` and run with the same installed `intk`.

## Enum and Literal choices

Toolkit validates `Enum` and `Literal` choices and includes their values in task help. Pass an enum's **value**, not its member name. A task receives an enum instance; a string Literal remains a string. Optional unions such as `Mode | None` and `Literal["fast", "safe"] | None` are also recognized.

Keep Enum/Literal and completion `Annotated` annotations as runtime objects in the task module, as in these examples. Current extraction for those features inspects the function signature directly and does not universally resolve string annotations from `from __future__ import annotations`. Path and Field extraction have additional type-hint resolution, but that is not full parity for every annotation feature.

```python
from enum import Enum
from typing import Annotated, Literal

from invoke_toolkit import Context, task


class Mode(str, Enum):
    FAST = "fast"
    SAFE = "safe"


@task
def describe(
    ctx: Context,
    mode: Annotated[Mode, "Execution mode"] = Mode.SAFE,
    level: Literal["brief", "full"] = "brief",
) -> None:
    """Describe the selected settings without changing anything."""
    print(f"mode={mode.value}, level={level}")
```

```bash
intk --help describe
intk describe --mode fast --level full
```

Invalid choices stop execution before the task body. This is not a general runtime type validator: do not assume arbitrary annotations, union alternatives or numeric Literal strings get universal coercion. Use string-valued choices for an unambiguous CLI contract.

Origin: [#38](https://github.com/D3f0/invoke-toolkit/pull/38), extended completion in [#41](https://github.com/D3f0/invoke-toolkit/pull/41).

## Annotated help and completion callbacks

A string in `Annotated` supplies parameter help; a callable supplies completion. Explicit `@task(help={...})` entries override annotation help. Enum/Literal option text is combined with annotation descriptions unless overridden.

This full `tasks.py` reads allowed targets from the loaded configuration. Completion callbacks receive `(ctx, incomplete)` and return `list[str]`; they should filter their own suggestions and avoid writes or expensive import-time work.

```python
from typing import Annotated

from invoke_toolkit import Collection, Context, task


def complete_target(ctx: Context, incomplete: str) -> list[str]:
    targets = ctx.get_config_value("deploy.targets", default=[])
    return sorted(target for target in targets if target.startswith(incomplete))


@task
def describe_target(
    ctx: Context,
    target: Annotated[str, "Configured target name", complete_target] = "staging",
) -> None:
    """Print a target; completion suggestions are not validation."""
    print(target)


ns = Collection(describe_target)
ns.configure({"deploy": {"targets": ["staging", "production"]}})
```

For CLI completion, put completion data in a project configuration file as well: collection defaults are not a substitute for already-loaded project configuration during callback execution. Save as `invoke.yaml` beside `tasks.py`:

```yaml
deploy:
  targets:
    - staging
    - production
completion:
  callback_timeout: 2.0
```

```bash
intk describe-target --target production
intk --complete -- intk describe-target --target
```

Callbacks take precedence over path/Enum/Literal suggestions when they return results. Suggestions do **not** constrain accepted task values. A callback timeout bounds the completion lookup, not the callback's own network or subprocess operations; a running thread is not forcibly cancelled. Set operation-level timeouts inside callbacks. See [completion installation and behavior](../humans/completion.md) and [persistent completion caching](caching.md#completion-callback-cache).

Origin: [#41](https://github.com/D3f0/invoke-toolkit/pull/41), positional support [#52](https://github.com/D3f0/invoke-toolkit/pull/52), configuration fixes [#94](https://github.com/D3f0/invoke-toolkit/pull/94) and [#101](https://github.com/D3f0/invoke-toolkit/pull/101).

## Path annotations and completion filters

Plain `pathlib.Path` annotations convert explicit strings to `Path` objects. The factories below add filesystem completion. **Call the factory**: `FilePath()`, not `FilePath`.

| Annotation factory | Value received | Completion |
| --- | --- | --- |
| `FilePath(exists=False, file_okay=True, dir_okay=True)` | `Path` | Files and/or directories |
| `FilePathStr(exists=False, file_okay=True, dir_okay=True)` | `str` | Same filters as `FilePath` |
| `FilePattern(pattern, exists=False)` | `Path` | Files matching a glob |
| `FilePatternStr(pattern, exists=False)` | `str` | Files matching a glob |
| `DirPath(exists=False)` | `Path` | Directories only |
| `DirPathStr(exists=False)` | `str` | Directories only |

```python
from invoke_toolkit import Context, FilePath, task


@task
def count_lines(
    ctx: Context,
    source: FilePath(exists=True, dir_okay=False),
) -> None:
    """Count lines in an existing UTF-8 file."""
    print(len(source.read_text(encoding="utf-8").splitlines()))
```

```bash
intk count-lines --source tasks.py
```

`exists=True` enables runtime existence and file/directory checks. With the default `exists=False`, the type filters guide completion but are not enforced on explicit values. `FilePattern("*.py")` filters suggestions, not accepted filenames. Completion stays within the current working-directory boundary; explicit paths are not sandboxed by that boundary. Read permissions, encoding and application-specific requirements remain your task's responsibility.

Origin: [#41](https://github.com/D3f0/invoke-toolkit/pull/41). For execution-time defaults and managed file contents, see [Fields](fields.md), not the completion factories.
