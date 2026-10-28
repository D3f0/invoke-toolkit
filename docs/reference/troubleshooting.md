# Troubleshooting

## Wrong executable or missing tasks

`intk`, `invoke-toolkit`, and `inv` are Toolkit's installed commands. A separate Invoke installation can also own `inv`; use `intk`, or `uv run intk` for a project environment, to choose explicitly.

```console
intk --version
intk --help
intk --search-root ./automation --list
intk --collection local_tasks --list
```

A normal collection is discovered from `tasks.py`; `local_tasks.py` augments it under `local`. Installed entry-point plugins live in the interpreter environment running the command, not every environment on the machine. `-x` enables built-ins. See [installation](../getting-started/installation.md), [collections](../guides/collections.md), and [plugins](../guides/plugins.md).

The main task or alias wins if it already owns the name `local`; Toolkit warns and skips the additional local file. Do not assume an existing `local` subcollection is protected by that guard. Separate local files use path-derived module names to avoid cross-directory collisions. Self-referential aliases are warned about and removed. Similar task/collection names are suggested for typos, including mistyped help targets; a suggestion never executes another task for you.

## Completion is empty or slow

Install completion for the executable and shell you actually use:

```console
intk -x shell.install-completions --shell fish
intk -x shell.completion-status
```

Start a new shell after changing startup files. Use `--search-root` when your task collection is outside the current directory. Enum/Literal/path annotations or a callback supply argument choices; free-form positional values do not need irrelevant task-name suggestions.

For expensive installed plugins, opt out of **plugin completion only**:

```yaml
completion:
  disable_plugins: true
```

Or set `INVOKE_COMPLETION_DISABLE_PLUGINS=1` for the completion process. Normal execution/listing still discovers plugins. Cache expensive completion callbacks and configure their timeout separately from task-result caching. See [completion](../humans/completion.md).

## A PEP 723 script ignores project dependencies

That is uv's inline-script behavior: metadata dependencies define an isolated environment even inside a project. Declare the packages the script imports in its `# /// script` block. Toolkit's project configuration is separate: `script()` loads it from the **working directory**, not automatically the script's parent directory.

```console
uv run tasks.py --help
uv run tasks.py --list --list-format json
```

Put `script()` after task definitions, preferably under a `__main__` guard for import reuse. Help/listing still executes module imports; never put deployments or network operations at module scope. See [PEP 723](../pep723/index.md).

## Changed-task discovery is empty or errors

`--list-changed` compares current task definitions to Git `HEAD`, including staged and unstaged edits. It ignores formatting/comments/line movement and indirect changes to imported functions, helpers, or globals. In a Git repository, a file absent from `HEAD`, including a repository without a commit, makes its tasks new.

No changes is a successful empty listing. Missing Git or a non-Git directory is an error for `--list-changed`, not for ordinary task listing. Color follows Rich terminal detection and `NO_COLOR`; use JSON for parsing. Do not interpret the list as a dependency-aware build impact analysis.

## Async command never ran

Inside `async def` tasks, **await** `ctx.run()` or use `await ctx.run_async()`. Synchronous tasks retain blocking semantics, even in mixed pre/post graphs. Helpers called inside an async task must also await async commands.

Async commands are noninteractive and buffer output until exit. They reject PTY, interactive stdin, stream watchers, and their own `asynchronous`/`disown` options. Use synchronous tasks for interactive commands and `sudo`. Concurrency is explicit through `ctx.gather()` or asyncio primitives, not automatic task parallelism. See [async tasks](../guides/async.md).

## Plugin lifecycle command rejects the environment

`plugin.add/link/update/remove` require a persistent `uv tool install invoke-toolkit` environment. They intentionally reject `uvx`, project `uv run`, and other installation managers. Install a plugin into the same environment as Toolkit; use manual `pipx inject` for pipx. Updating plugins does not update Toolkit itself. See [plugins](../guides/plugins.md).

## Configuration or dynamic values look wrong

Read the [configuration guide](../guides/configuration.md) for the supported command forms, config locations, and schema validation. `Field` lookup prefers explicit values, environment, and resolved task config before declared defaults/factories. URI resolvers return **text**: Toolkit materializes it as temporary files only for path fields. Factories and URI resolvers do not run for help/list/completion. See [Fields](../guides/fields.md).

## Output is not JSON or a secret appears

`--list-format json` controls task **listings**, not task results. Return-value `autoprint` is a presentation helper, not JSON serialization. Emit JSON explicitly, keep logs on stderr, and avoid Rich markup/wrapping for a machine-data stream. See [AI-agent contracts](../agents/index.md).

Output redaction is not a general security boundary. It does not scrub command arguments, arbitrary Python output, captured result values, native async output, files, or all possible secret encodings. Avoid putting secrets in commands and do not rely on scoped redaction restoration guarantees. See [execution and redaction](../guides/execution.md).

## Documentation build or Pages deployment

```console
uv run --locked --group doc zensical build --clean --strict
```

Documentation tooling needs Python 3.11+; the library still supports Python 3.10+. Fix missing pages/anchors rather than weakening strict validation.

For initial Pages deployment, select **GitHub Actions** as the source under repository **Settings → Pages** and restrict the `github-pages` environment to `main`. The workflow builds PRs but deploys only successful `main` builds. A local build does not mean the public site is published. See [contributor workflow](https://github.com/D3f0/invoke-toolkit/blob/main/CONTRIBUTING.md#documentation).

## Fix sources

[Namespace collision #133](https://github.com/D3f0/invoke-toolkit/pull/133), [local module isolation #123](https://github.com/D3f0/invoke-toolkit/pull/123), [alias guard #116](https://github.com/D3f0/invoke-toolkit/pull/116), [typo suggestions #140](https://github.com/D3f0/invoke-toolkit/pull/140), [completion performance #144](https://github.com/D3f0/invoke-toolkit/pull/144), [PEP 723 config #104](https://github.com/D3f0/invoke-toolkit/pull/104), [async fixes #127](https://github.com/D3f0/invoke-toolkit/pull/127).
