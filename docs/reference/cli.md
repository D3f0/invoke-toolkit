# CLI reference

Invoke Toolkit installs `intk`, `invoke-toolkit`, and `inv`. Use `intk` to make the selected implementation explicit when Invoke is also installed. The underlying task CLI retains [Invoke's core options](https://docs.pyinvoke.org/en/latest/invoke.html), task chaining, aliases, pre/post tasks, and argument conventions.

```console
intk --help
intk --help hello
intk hello --name Ada
```

For a [PEP 723 task script](../pep723/index.md), replace `intk` with `uv run tasks.py`.

## Discovery and listing

| Option | Meaning |
| --- | --- |
| `--list`, `-l` | List tasks; an optional namespace limits the scope |
| `--list-format`, `-F` | `flat`, `nested`, or `json`; changes a listing's format, does not request a listing by itself |
| `--list-depth`, `-D` | Limit nested listing depth |
| `--list-tasks`, `--lt` | List the primary collection, including its own namespaces, without plugin collections |
| `--list-plugins`, `--lp` | List plugin collections without the primary tasks |
| `--list-changed` | List task definitions created or updated relative to Git `HEAD` |
| `--search-root`, `-r` | Root directory for task-file discovery |
| `--collection`, `-c` | Select a task module instead of the default `tasks` |
| `--internal-col`, `-x` | Include Toolkit's built-in collections |

```console
intk --list --list-format json
intk --list-tasks --list-format json
intk --list-plugins --list-format nested
intk --list-changed --list-format json
intk --list deploy --list-changed
intk --search-root ./automation --list
intk -x --list
```

When both listing filters are supplied, `--list-tasks` takes precedence over `--list-plugins`. Changed-task filtering can combine with listing scopes and formats. Git comparison includes staged and unstaged task-definition edits; see [PEP 723 and Git discovery](../pep723/index.md). JSON uses Invoke's collection/task schema, not a schema for task arguments or execution results.

Task discovery imports Python modules and installed plugins. Keep imports free of operational side effects; help/listing is not a sandbox.

## Terminal presentation

| Toolkit option | Meaning |
| --- | --- |
| `--disable-status`, `--ds` | Disable Rich status contexts; useful for debugging and noninteractive execution |
| `--show-command-output`, `-O` | Show recent synchronous subprocess output beneath an active status spinner |
| `--init-shell` | Initialize the synchronous runner shell from `$SHELL` |
| `--redact-stdout`, `--So` | Redact configured environment secrets from rendered stdout |
| `--redact-stderr`, `--Se` | Redact configured environment secrets from rendered stderr |
| `--redact-pattern`, `--Sp` | Supply redaction patterns; see the output redaction guide |

```console
intk --disable-status hello
intk --show-command-output build
```

Rich respects terminal color detection and `NO_COLOR`. Disabling status does not turn every task into a machine-readable-output task. Redaction is limited to supported output paths; it does not secure process arguments, environment access, files, or captured result objects. See [Rich output](../humans/rich-output.md) and [execution and redaction](../guides/execution.md).

## Completion

```console
intk --print-completion-script bash
intk -x shell.install-completions --shell fish
intk -x shell.completion-status
intk -x shell.uninstall-completions --shell fish
```

Generated scripts and installer support Bash, Zsh, and Fish. The installer writes shell configuration files; inspect its help and target shell first. See [completion callbacks, paths, and performance](../humans/completion.md).

## Built-in library tasks

Built-ins require `-x`. Inspect help before operations that change configuration, packages, or shell startup files.

| Namespace | Operations | Guide |
| --- | --- | --- |
| `config` | Get, set, and unset configuration; inspect formats and validation options in task help | [Configuration](../guides/configuration.md) |
| `create` | Generate a task plugin or URI-provider package | [Package templates](../guides/packages.md) |
| `plugin` | List/add/link/update/remove plugins in a persistent uv tool environment | [Plugins](../guides/plugins.md) |
| `shell` | Install/remove/inspect shell completions | [Completion](../humans/completion.md) |

## Inherited Invoke execution options

`--echo`, `--hide`, `--pty`, `--warn-only`, `--command-timeout`, `--dry`, `--no-dedupe`, and the remainder after `--` are Invoke interfaces. Toolkit requires Invoke **>=3.0.3**; `ctx.remainder` is inherited from Invoke 3. Do not assume `--dry` prevents arbitrary Python task-body side effects: it controls command execution. Async subprocesses support a narrower set of options than the synchronous runner; [async limitations](../guides/async.md) are explicit.

## Feature sources

[Listing filters #120](https://github.com/D3f0/invoke-toolkit/pull/120), [changed tasks #146](https://github.com/D3f0/invoke-toolkit/pull/146), [status #19](https://github.com/D3f0/invoke-toolkit/pull/19), [shell initialization #25](https://github.com/D3f0/invoke-toolkit/pull/25), [live output #105](https://github.com/D3f0/invoke-toolkit/pull/105), [completion installer #64](https://github.com/D3f0/invoke-toolkit/pull/64), [Invoke 3 compatibility #114](https://github.com/D3f0/invoke-toolkit/pull/114).
