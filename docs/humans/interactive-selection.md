# Interactive selection

Toolkit's fzf helpers turn a list or command output into a terminal selector. When the external [fzf executable](https://github.com/junegunn/fzf) is missing, the default fallback is a simpler Rich table and numbered prompt—not full fzf feature parity ([PR #80](https://github.com/D3f0/invoke-toolkit/pull/80)).

Install fzf using its [official installation instructions](https://github.com/junegunn/fzf#installation) and make it available on `PATH`. It is not a Python extra. `is_fzf_available()` checks whether the executable can be found.

## Accept an explicit argument before prompting

This complete `tasks.py` works for a person at a terminal and supports noninteractive callers that provide a value:

```python
from invoke_toolkit import Context, task
from invoke_toolkit.utils.fzf import select


@task
def choose(ctx: Context, environment: str = "") -> None:
    """Choose and print an environment; supply --environment to skip the prompt."""
    environments = ["development", "staging", "production"]
    if not environment:
        selected = select(ctx, environments, prompt="Choose environment")
        if selected is None:
            ctx.print_err("Selection cancelled.")
            return
        environment = selected
    if environment not in environments:
        ctx.rich_exit("Unknown environment.", exit_code=2)
    print(environment)
```

```sh
uv run intk choose
uv run intk choose --environment staging
```

The explicit argument bypasses the prompt. Agents and CI should use that path rather than trying to drive the interactive selector. Keep prompts inside task bodies: listing, help and completion still import the module.

`select(ctx, choices, ...)` returns a string for a single selection, a list with `multi=True`, and `None` or an empty list on cancellation or no result according to that mode.

## Multi-selection, previews and fzf options

This complete example selects names of files from the process's current directory:

```python
from pathlib import Path

from invoke_toolkit import Context, task
from invoke_toolkit.utils.fzf import select


@task
def choose_files(ctx: Context) -> None:
    """Interactively select file names without opening or modifying files."""
    choices = sorted(path.name for path in Path.cwd().iterdir() if path.is_file())
    selected = select(
        ctx,
        choices,
        prompt="Choose files",
        multi=True,
        header="Available files",
        height="60%",
        select_1=True,
        exit_0=True,
    )
    for filename in selected or []:
        print(filename)
```

```sh
uv run intk choose-files
```

With fzf, `multi=True` enables its multi-select UI. Use `preview` for an fzf preview command and `preview_window` for its layout. Extra keyword names become flags with underscores changed to dashes; true booleans add flags, while other values become `--flag=value`. Values containing spaces are quoted by the implementation ([PR #81](https://github.com/D3f0/invoke-toolkit/pull/81)).

**Command and preview strings are executable shell content.** Quoting improvements do not make arbitrary untrusted options, file names or preview templates safe. Keep command templates trusted and use deliberate argument quoting when building commands; see [execution](../guides/execution.md).

If a workflow depends on fzf-only functionality, set `use_fallback=False`; selection raises `RuntimeError` when fzf is unavailable or forced off instead of quietly using the reduced selector.

## Select from command output

`select_from_command(ctx, command, ...)` runs a command with `hide=True, warn=True`, then presents its stdout lines. Command failure returns no selection rather than raising a task failure automatically; inspect or handle that result in your workflow.

This complete example requires Git and a repository with local branches. It prints a selected branch without checking it out:

```python
from invoke_toolkit import Context, task
from invoke_toolkit.utils.fzf import select_from_command


@task
def choose_branch(ctx: Context) -> None:
    """Select and print a local Git branch without changing the checkout."""
    branch = select_from_command(
        ctx,
        "git for-each-ref --format='%(refname:short)' refs/heads",
        prompt="Choose branch",
    )
    if branch is None:
        ctx.print_err("No branch selected, or branch discovery failed.")
        return
    print(branch)
```

```sh
uv run intk choose-branch
```

The command executes even when selection falls back to Rich. Interactive helpers are synchronous; do not assume they are suitable inside a native async task.

## Understand the reduced Rich fallback

When fzf is missing or disabled, the fallback:

- Shows a numbered table and accepts one number or `q` to quit.
- Supports `select_1=True` for a single available choice and empty-result handling with `exit_0`.
- Does **not** offer fuzzy filtering, preview panes or the full fzf option set.
- With `multi=True`, warns that true multi-select is unavailable and returns at most one chosen item in a list.
- Returns no selection for invalid input, interruption or EOF; it does not continuously re-prompt after every invalid entry.

Configure `invoke.yaml` with both documented fuzzy-finder keys:

```yaml
fuzzy_finder:
  show_warnings: true
  force_fallback: true
```

For one invocation in a POSIX shell:

```sh
INVOKE_FUZZY_FINDER_FORCE_FALLBACK=1 uv run intk choose
```

Set `force_fallback: false` to allow fzf again. Set `show_warnings: false` to silence the once-per-process missing/disabled-fzf notice. These notices use `ctx.print_err()` ([PR #83](https://github.com/D3f0/invoke-toolkit/pull/83)); the numbered fallback UI itself is a human-facing stdout interface, so do not use it in a JSON-only execution path. Configuration access was simplified in [PR #82](https://github.com/D3f0/invoke-toolkit/pull/82).

[Human workflow](index.md) · [Rich output](rich-output.md) · [Configuration](../guides/configuration.md) · [Agent contracts](../agents/index.md) · [API reference](../reference/api.md)
