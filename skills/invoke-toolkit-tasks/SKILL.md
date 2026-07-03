---
name: invoke-tasks
description: >
  Describes how to create invoke toolkit tasks
---

> # Pre-requsites
> 1. uv package manager

# Skill: invoke-toolkit Task Creation

Use this skill when the user asks to create, write, or explain tasks for **invoke-toolkit** —
including `@task` decorator parameters, how Python type annotations map to CLI arguments, 
and how to use `ToolkitContext` helpers inside a task.

## Where to find/add/edit tasks

The `@task` decorated python functions can be added to the following locations:

1. To the tasks.py in the root of a git repo. To get the root of the repo `git rev-parse --show-toplevel`
2. Added to the `local_tasks.py` in the root of the repo
3. In a invoke-toolkit plugin, which can be detected by the presence of a pyproject.toml in the path
   having a [project.entry-points."invoke_toolkit.collection"]
   the tasks should be added to the `src/<path>/tasks.py` if it exists. 
   If it doesn't it means the module has been split and the src folder should be 
   scanned for modules where `@task` decorated functions are available.

When working with tasks.py evaluate if they are PEP723 scripts, they will start with:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "invoke-toolkit>=0.0.59",
# ]
# ///
from invoke_toolkit import task, Context, script

@task()
def hello_world(ctx: Context):
    ctx.run("echo 'hello world'")

script()
```

It's important to keep the `script()` at the end of the file. Otherwise stand-alone
script logic for `uv run tasks.py ...` won't work.


## 1. The `@task` Decorator

Import from `invoke_toolkit`:

```python
from invoke_toolkit import task, Context
```

Both forms are valid:

```python
@task                          # no parentheses — uses all defaults
def my_task(ctx: Context): ...

@task()                        # parentheses — same defaults
def my_task(ctx: Context): ...

@task(name="deploy", aliases=["d"])   # with options
def deploy_task(ctx: Context): ...
```

### Decorator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str \| None` | `None` | Override the CLI name (default: function name with `_` → `-`) |
| `aliases` | `Sequence[str] \| None` | `None` | Alternative CLI names, e.g. `aliases=["d", "dep"]` |
| `default` | `bool \| None` | `False` | Make this the default task in its namespace |
| `positional` | `Sequence[str] \| None` | `None` | List of parameter names to treat as positional args |
| `optional` | `Sequence[str] \| None` | `None` | List of flag names whose value is optional (flag alone is valid) |
| `iterable` | `Sequence[str] \| None` | `None` | List of parameter names that accept multiple values (`--tag a --tag b`) |
| `incrementable` | `Sequence[str] \| None` | `None` | List of flag names that increment on each use (`-v -v -v` → `3`) |
| `bool_flags` | `tuple[str, ...]` | `()` | Extra names that should be treated as boolean flags |
| `autoprint` | `bool` | `False` | Automatically print the return value of the task |
| `help` | `dict[str, str] \| None` | `None` | Explicit per-parameter help strings (merged with `Annotated` docs; explicit takes precedence) |
| `pre` | `list[Callable] \| None` | `None` | Tasks to run before this task |
| `post` | `list[Callable] \| None` | `None` | Tasks to run after this task |
| `klass` | `Type[ToolkitTask]` | `ToolkitTask` | Task class to use (rarely overridden) |
| `proctitle` | `str \| None` | `None` | Set the OS process title while the task runs (restored on exit) |
| `cache` | `bool \| dict \| None` | `None` | Cache the return value. `True` = permanent cache; `{"ttl": 3600}` = 1-hour TTL; `{"ttl": 600, "ignore_args": ["verbose"]}` = ignore some args in cache key |

---

## 2. How Python Parameters Map to CLI Arguments

Invoke reads the function signature and converts each parameter (after `ctx`) into a CLI argument. invoke-toolkit extends this with type-aware auto-conversion.

### Basic Type Mapping

| Python annotation | CLI form | Notes |
|-------------------|----------|-------|
| `str` | `--name VALUE` | Default type |
| `int` | `--count 5` | Auto-cast to int |
| `float` | `--ratio 0.5` | Auto-cast to float |
| `bool` (default `False`) | `--verbose` / `--no-verbose` | Boolean flag pair |
| `list[str]` | `--tag a --tag b` | Use `iterable=["tag"]` |
| `pathlib.Path` | `--path /some/file` | String auto-converted to `Path` object by invoke-toolkit |

A parameter **without a default** becomes a **required** CLI argument:
```python
@task
def build(ctx: Context, target: str) -> None:
    ...
# inv build --target myapp   ← required
```

A parameter **with a default** becomes **optional**:
```python
@task
def build(ctx: Context, target: str = "myapp") -> None:
    ...
# inv build                  ← uses default
# inv build --target other   ← override
```

### Boolean Flags

Any parameter typed as `bool` (with a `False` default) generates a `--flag` / `--no-flag` pair:
```python
@task
def deploy(ctx: Context, dry_run: bool = False) -> None:
    ...
# inv deploy --dry-run
# inv deploy --no-dry-run
```

### Positional Arguments

Use `positional=["param"]` to make a parameter positional:
```python
@task(positional=["path"])
def read(ctx: Context, path: str) -> None:
    ...
# inv read /etc/hosts         ← no --path needed
```

### Iterable (multi-value) Arguments

Use `iterable=["tags"]` for parameters that can be provided multiple times:
```python
@task(iterable=["tags"])
def release(ctx: Context, tags: list = []) -> None:
    ...
# inv release --tags v1 --tags latest
```

### Incrementable Flags

Use `incrementable=["verbosity"]` for counters that grow with repeated flags:
```python
@task(incrementable=["verbosity"])
def run(ctx: Context, verbosity: int = 0) -> None:
    ...
# inv run -v -v -v   → verbosity = 3
```

### Optional Flags (value-optional)

Use `optional=["output"]` when the flag value itself is optional (the flag can be used alone):
```python
@task(optional=["output"])
def show(ctx: Context, output: str = None) -> None:
    ...
# inv show            → output = None
# inv show --output   → output = ""  (flag present, no value)
# inv show --output file.txt → output = "file.txt"
```

---

## 3. Enum and Literal Types — Auto-Validated Choices

invoke-toolkit automatically:
- Discovers `Enum` and `Literal` parameter types
- Injects available choices into the help text
- Converts the incoming string CLI value to the Enum instance (or validates it against Literal values)
- Prints a rich error and exits if an invalid value is passed

### Enum Parameters

```python
from enum import Enum
from invoke_toolkit import task, Context

class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

@task
def paint(ctx: Context, color: Color = Color.GREEN) -> None:
    """Paint with a color."""
    print(f"Painting with {color.value}")

# inv paint --color red     → color is Color.RED (the Enum member)
# inv paint --color purple  → rich error: "Invalid value 'purple'..."
# Help shows: --color     Choices: red, green, blue
```

`Optional[Color]` / `Color | None` are also handled:
```python
@task
def paint(ctx: Context, color: Color | None = None) -> None: ...
```

### Literal Parameters

```python
from typing import Literal

@task
def log(ctx: Context, level: Literal["debug", "info", "warning", "error"] = "info") -> None:
    print(f"Log level: {level}")

# inv log --level debug
# inv log --level oops  → rich error exit
```

---

## 4. Self-Documenting Parameters with `Annotated`

Use `Annotated[type, "help text"]` to embed per-parameter documentation directly in the signature. This is merged with (and overridden by) the explicit `help={}` dict.

```python
from typing import Annotated
from invoke_toolkit import task, Context

@task
def deploy(
    ctx: Context,
    environment: Annotated[str, "Target environment (e.g. staging, production)"],
    dry_run: Annotated[bool, "Simulate without making changes"] = False,
) -> None:
    """Deploy the application."""
    ...
```

The `Annotated` metadata string becomes the help text shown in `inv --help deploy`.

---

## 5. Path Type Annotations

`pathlib.Path` parameters (and the convenience wrappers below) are automatically converted from the string received at the CLI to a `Path` object.

### Convenience Path Types

| Type factory | Returns | Completes | Validates |
|---|---|---|---|
| `FilePath(exists=False, file_okay=True, dir_okay=True)` | `Path` | files + dirs | optionally `exists` |
| `FilePathStr(...)` | `str` | files + dirs | optionally `exists` |
| `FilePattern("*.py", exists=False)` | `Path` | glob-matched files | optionally `exists` |
| `FilePatternStr("*.py", ...)` | `str` | glob-matched files | optionally `exists` |
| `DirPath(exists=False)` | `Path` | directories only | optionally `exists` |
| `DirPathStr(exists=False)` | `str` | directories only | optionally `exists` |

```python
from invoke_toolkit import task, Context, FilePath, FilePattern, DirPath

@task
def process(ctx: Context, file: FilePath(exists=True, dir_okay=False)) -> None:
    """Process an existing file."""
    print(file)            # file is a pathlib.Path

@task
def lint(ctx: Context, source: FilePattern("*.py")) -> None:
    """Lint a Python file."""
    ctx.run(f"ruff check {source}")

@task
def export(ctx: Context, output: DirPath(exists=True)) -> None:
    """Export to a directory."""
    ctx.run(f"cp -r dist/ {output}/")
```

These also enable **shell tab-completion** when using invoke-toolkit's completion system.

---

## 6. Dynamic Completion Callbacks via `Annotated`

Place a callable as the third element of `Annotated` to provide dynamic shell completions:

```python
from typing import Annotated
from invoke_toolkit import task, Context

def complete_envs(ctx: Context, incomplete: str = "") -> list[str]:
    envs = ["development", "staging", "production"]
    return [e for e in envs if e.startswith(incomplete)]

@task
def deploy(
    ctx: Context,
    environment: Annotated[str, "Target environment", complete_envs],
) -> None:
    ctx.run(f"deploy.sh {environment}")
```

Callback signature: `(ctx: Context, incomplete: str = "") -> list[str]`

---

## 7. Pre/Post Tasks and `call()`

Chain tasks using `pre` and `post`. Use `call()` to pass arguments to pre/post tasks:

```python
from invoke_toolkit import task, call, Context

@task
def clean(ctx: Context, all: bool = False) -> None:
    ctx.run("rm -rf dist" if all else "rm -rf dist/*.pyc")

@task(pre=[clean])
def build(ctx: Context) -> None:
    ctx.run("python -m build")

@task(pre=[call(clean, all=True)])
def release(ctx: Context) -> None:
    ctx.run("twine upload dist/*")
```

---

## 8. Caching

```python
from invoke_toolkit import task, Context

# Permanent cache (no TTL)
@task(cache=True)
def fetch_config(ctx: Context, env: str) -> dict:
    return expensive_api_call(env)

# Cache with TTL (seconds)
@task(cache={"ttl": 3600})
def fetch_data(ctx: Context, name: str) -> dict:
    return fetch_from_api(name)

# Cache but ignore some args in the cache key
@task(cache={"ttl": 600, "ignore_args": ["verbose"]})
def search(ctx: Context, query: str, verbose: bool = False) -> list:
    return do_search(query, verbose=verbose)
```

Cache location is derived from the git repository root + `platformdirs`. Requires the `diskcache` package. Cache activity is logged with `-d` (debug mode). Use `clear_task_cache()` or `cache_stats()` to manage the cache.

---

## 9. `autoprint`

When `autoprint=True`, the task's return value is automatically printed after it completes:

```python
@task(autoprint=True)
def version(ctx: Context) -> str:
    return "1.2.3"

# inv version  →  prints "1.2.3"
```

---

## 10. `proctitle` — OS Process Title

Sets the OS process title while the task runs (restored on exit). Also updates the tmux window name when inside tmux:

```python
@task(proctitle="Building project")
def build(ctx: Context) -> None:
    ctx.run("python -m build")
# Process title shown in `ps` / `htop` is "Building project" while running
```

---

## 11. `ToolkitContext` Helper Methods

The first parameter of every task must be typed as `Context` (alias for `ToolkitContext`). It provides all standard Invoke methods plus these extras:

### Running Commands

```python
ctx.run("command")           # Run a shell command, returns Result
ctx.sudo("command")          # Run with sudo (auto-responds to password prompt)
```

### Directory and Prefix Context Managers

```python
with ctx.cd("/var/www"):
    ctx.run("ls")            # → "cd /var/www && ls"
    with ctx.cd("html"):
        ctx.run("ls")        # → "cd /var/www/html && ls"

with ctx.prefix("source .venv/bin/activate"):
    ctx.run("python app.py") # → "source .venv/bin/activate && python app.py"
```

### Output (Rich)

```python
ctx.print("[green]Success![/green]")       # Rich markup to stdout
ctx.print_err("[red]Error![/red]")         # Rich markup to stderr
ctx.console.print(...)                     # Full Rich Console instance (stdout)
ctx.inspect(obj)                           # Rich inspect() on any object
```

### Status Spinner

```python
with ctx.status("Loading..."):
    time.sleep(2)

ctx.status_update("Still loading...")     # Update spinner text
ctx.status_stop()                         # Dismiss all spinners (useful for debug)
```

### Exit

```python
ctx.rich_exit("Something went wrong", exit_code=1)   # Prints rich message, then sys.exit(exit_code)
```

### Configuration Access

```python
# Dot-notation config lookup
host = ctx.get_config_value("database.host", default="localhost")
key  = ctx.get_config_value("api.key", required=True)          # exits if missing
key  = ctx.get_config_value("api.key", exit_message="API key required", exit_code=2)

# Typed schema config
from invoke_toolkit.config import config_schema, ConfigSchema

@config_schema("myapp")
class MyConfig(ConfigSchema):
    debug: bool = False
    workers: int = 4

@task
def serve(ctx: Context) -> None:
    cfg = ctx.get_schema(MyConfig)       # auto-uses "myapp" path
    cfg = ctx.get_schema(MyConfig, "custom.path")  # explicit path
    print(cfg.workers)
```

### Process Title (context manager form)

```python
@task
def process(ctx: Context) -> None:
    with ctx.proctitle("Processing files"):
        do_work()
    # title restored here
```

### Redacting Secrets from Output

```python
import os

@task
def deploy(ctx: Context) -> None:
    with ctx.redact("out"):                       # redact all env vars from stdout
        ctx.run(f"deploy.sh {os.environ['TOKEN']}")

    with ctx.redact({"out": "*KEY", "err": "*SECRET"}):  # pattern-based redaction
        ctx.run("sensitive_command")
```

### Current Working Directory

```python
print(ctx.cwd)    # current dir accounting for ctx.cd() nesting
```

---

## 12. Complete Example

```python
from enum import Enum
from typing import Annotated, Literal
from invoke_toolkit import task, call, Context, FilePath, DirPath

class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

def complete_branches(ctx: Context, incomplete: str = "") -> list[str]:
    import subprocess
    out = subprocess.check_output(["git", "branch", "--list"], text=True)
    branches = [b.strip().lstrip("* ") for b in out.splitlines()]
    return [b for b in branches if b.startswith(incomplete)]

@task
def lint(ctx: Context) -> None:
    """Run linter."""
    ctx.run("ruff check .")

@task(
    pre=[lint],
    aliases=["d"],
    autoprint=False,
    proctitle="Deploying",
    cache={"ttl": 300, "ignore_args": ["dry_run"]},
)
def deploy(
    ctx: Context,
    env: Annotated[Environment, "Target environment"] = Environment.DEV,
    branch: Annotated[str, "Git branch to deploy", complete_branches] = "main",
    config_file: FilePath(exists=True, dir_okay=False) = None,
    output_dir: DirPath(exists=False) = None,
    dry_run: Annotated[bool, "Simulate without side-effects"] = False,
    level: Literal["debug", "info", "warning"] = "info",
) -> None:
    """Deploy the application to the target environment."""
    with ctx.status(f"Deploying to {env.value}..."):
        if dry_run:
            ctx.print(f"[yellow]DRY RUN:[/yellow] would deploy {branch} → {env.value}")
            return

        db_host = ctx.get_config_value("database.host", default="localhost")
        ctx.run(f"deploy.sh --env {env.value} --branch {branch} --db {db_host}")

    ctx.print(f"[green]Deployed {branch} to {env.value}![/green]")
```

## Finding more documentation

Run this command:

```shell
# For the top level interface
uv run --with invoke-toolkit -m pydoc invke_toolkit
# for a specific function
uv run --with invoke-toolkit -m pydoc invke_toolkit.task
uv run --with invoke-toolkit -m pydoc invke_toolkit.Context
uv run --with invoke-toolkit -m pydoc invke_toolkit.run

```
