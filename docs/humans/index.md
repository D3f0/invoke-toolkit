# For humans

Use the same Python tasks you would expose to an agent, with a terminal interface designed for people: useful help, completion, Rich progress and optional interactive selection.

Start with the [quickstart](../getting-started/quickstart.md) or [migrate your Invoke collection](../getting-started/from-invoke.md).

## Find and inspect a task

From a project with Toolkit installed and the quickstart's `tasks.py`:

```sh
uv run intk --list
uv run intk --help hello
uv run intk hello --name teammate
```

These are Invoke-style discovery and execution operations. Toolkit adds close-name suggestions after an unknown task or help target; it also considers aliases and nested collection names. A suggestion is informational, not an automatic retry ([PR #140](https://github.com/D3f0/invoke-toolkit/pull/140)).

For projects with plugins, narrow the listing:

```sh
uv run intk --list-tasks
uv run intk --list-plugins
```

The main-task view retains non-plugin subcollections; the plugin view shows installed entry-point collections ([PR #120](https://github.com/D3f0/invoke-toolkit/pull/120)). See [collections](../guides/collections.md) and the [CLI reference](../reference/cli.md).

## Make the terminal helpful

### Rich messages, status and command panels

[Rich output](rich-output.md) covers stdout versus stderr, styled messages, inspection, disabling animation for debugging, and `--show-command-output` (`-O`). The panel shows the latest three subprocess lines during a status block and disappears when it ends ([PR #105](https://github.com/D3f0/invoke-toolkit/pull/105)). It is not a permanent build log.

## Autocompletion: discover without memorizing

Install completion for the `intk` executable on your `PATH`, then start a new shell:

```sh
intk -x shell.install-completions --shell fish
```

Use `--shell bash` or `--shell zsh` for those shells. Type `intk ` and press Tab
to discover tasks; type `intk -x ` and press Tab for built-in collections.
For an argument backed by Enum, Literal, a path marker or a callback, press Tab
after its flag to discover values instead of memorizing them.

The [autocompletion guide](completion.md) covers shell startup changes, typed
choices, paths, callbacks using loaded configuration, callback timeouts and
optional persistent caching. Those caches are separate from task-result caching
([PR #64](https://github.com/D3f0/invoke-toolkit/pull/64),
[PR #76](https://github.com/D3f0/invoke-toolkit/pull/76),
[PR #101](https://github.com/D3f0/invoke-toolkit/pull/101),
[PR #139](https://github.com/D3f0/invoke-toolkit/pull/139)).

### Record a terminal demo for browser replay

Use [asciinema](https://docs.asciinema.org/manual/cli/) to save a terminal
session as a lightweight `.cast` file, then replay it in a browser with
[asciinema player](https://docs.asciinema.org/manual/player/quick-start/).
It is a good fit for showing Tab completion, Rich status and interactive
selection. See [recording and sharing a demo](completion.md#record-and-share-an-autocompletion-demo)
for capture commands, publishing choices and a GIF alternative.

## Interactive selection

[Interactive selection](interactive-selection.md) lets a task present choices with fzf or a reduced Rich numbered fallback. Keep prompts out of automation paths: accept an explicit argument first and prompt only when it is omitted ([PR #80](https://github.com/D3f0/invoke-toolkit/pull/80)).

## Carry the workflow in one file

[PEP 723](../pep723/index.md) puts dependencies beside task code so uv can prepare a portable script environment. Toolkit's `script()` provides help, listing and task invocation. Configuration still comes from the current working directory ([PR #104](https://github.com/D3f0/invoke-toolkit/pull/104)).

For Git-managed task files, [changed-task listing](../pep723/index.md#list-changed-task-definitions) compares task definitions with `HEAD`, including staged and unstaged edits ([PR #146](https://github.com/D3f0/invoke-toolkit/pull/146)). It does not trace changes through helpers or global variables.

## Author tasks that serve both audiences

Use [typed arguments](../guides/typed-arguments.md) for discoverable input contracts and [configuration](../guides/configuration.md) for project settings. Keep task modules quiet at import time: even help and listing execute top-level Python code. If task output will be parsed, follow the [agent output contract](../agents/index.md) rather than relying on terminal formatting.

[Execution and redaction boundaries](../guides/execution.md) · [Troubleshooting](../reference/troubleshooting.md) · [Improvement history](../reference/improvements.md)
