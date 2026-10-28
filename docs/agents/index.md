# For AI agents

Invoke Toolkit is a Python automation library whose task interfaces can be used by humans and AI agents. An agent needs no separate protocol integration: discover the tasks, inspect their help and execute explicit commands in the correct environment and working directory.

The same task code can offer [Rich terminal feedback](../humans/rich-output.md) to a person or an explicit machine-readable contract to an agent. [PEP 723 task files](../pep723/index.md) make the dependency contract portable between those audiences.

## Discover, inspect, execute

Start in a trusted project with Toolkit installed ([installation](../getting-started/installation.md)). With the quickstart's `tasks.py`:

```sh
uv run intk --list --list-format json
uv run intk --help hello
uv run intk --disable-status hello --name agent
```

1. **Discover:** use both `--list` and `--list-format json` for normal JSON listing.
2. **Inspect:** read `--help TASK` for the task's docstring, flags, defaults and typed choices. Listing is a namespace description, not a complete parameter schema.
3. **Execute:** select an exact task name and supply explicit values for important arguments. Observe the command's exit status and output according to the task's declared contract.

For a portable file, use the matching script runner instead:

```sh
uv run --script portable_tasks.py --list --list-format json
uv run --script portable_tasks.py --help report
uv run --script portable_tasks.py --disable-status report --count 5
```

Create `portable_tasks.py` from the [complete PEP 723 example](../pep723/index.md#a-complete-runnable-script). Inline metadata defines the script environment and ignores surrounding project dependencies; Toolkit configuration still loads from the current working directory.

`--list-format json` alone does **not** request listing and is **not** a universal JSON mode. `--disable-status` removes spinner animation, but disabled status blocks can still print progress messages. Arbitrary task output remains under the author's control.

## Narrow discovery without inventing permissions

Toolkit adds main/plugin listing scopes ([PR #120](https://github.com/D3f0/invoke-toolkit/pull/120)):

```sh
uv run intk --list-tasks --list-format json
uv run intk --list-plugins --list-format json
uv run intk --list local --list-format json
```

The last command assumes a `local` collection such as the quickstart's `local_tasks.py`. Main-task listing includes non-plugin subcollections; plugin listing includes installed entry-point collections. A no-plugin result can be a human-readable successful message rather than a JSON document, so consumers must not assume every scoped command always produces parseable JSON in every empty state. Normal listing JSON retains Invoke's schema, with task/alias/default information and nested collections.

Listing scopes are filters, not execution permissions or plugin isolation. Imports still occur before listing. See [collections](../guides/collections.md), [plugins](../guides/plugins.md) and the [CLI reference](../reference/cli.md).

## Own the task output contract

There is no automatic JSON serialization of every task result. For a machine-facing task, emit a JSON document explicitly to stdout, send diagnostics to stderr and avoid extra output from imports, pre/post tasks or subprocesses.

Save this complete project `tasks.py`:

```python
import json

from invoke_toolkit import Context, task


@task
def report(ctx: Context, count: int = 3) -> None:
    """Return one JSON object; count must be nonnegative."""
    if count < 0:
        ctx.print_err("count must be nonnegative")
        raise SystemExit(2)
    ctx.print_err("Report generated.")
    print(json.dumps({"status": "ok", "count": count}, sort_keys=True))
```

```sh
uv run intk --list --list-format json
uv run intk --help report
uv run intk --disable-status report --count 5
```

This code reserves stdout for one serialized object and uses a nonzero exit code for its input error. It does not claim Toolkit applies that contract to other tasks. `autoprint=True` on a returned dict uses Rich rather than guaranteeing JSON; serialize explicitly.

### Capture output without a shell

From the same uv project, save this complete caller as `consume_report.py`:

```python
import json
import subprocess


result = subprocess.run(
    ["uv", "run", "intk", "--disable-status", "report", "--count", "5"],
    capture_output=True,
    text=True,
    check=False,
)
if result.returncode != 0:
    raise SystemExit(f"report failed ({result.returncode}): {result.stderr.strip()}")
data = json.loads(result.stdout)
print(data["count"])
```

```sh
uv run consume_report.py
```

The argument vector prevents shell interpretation in the caller. It does not sanitize commands that the invoked task itself builds. Choose the process's working directory deliberately: project discovery/configuration and PEP 723 script configuration have different roots, described in [configuration](../guides/configuration.md) and [PEP 723](../pep723/index.md#project-configuration-follows-the-current-directory).

## Treat imports as execution

Listing, help and completion import Python task modules and plugin modules. **Top-level Python statements execute**, including file writes, network calls, subprocesses and prompts. Toolkit has no sandbox, permission broker or guarantee of pure discovery.

- Keep execution-only work inside task functions.
- Use guarded `script()` entrypoints for importable standalone files; Toolkit's double-execution prevention is specific to its loader ([PR #17](https://github.com/D3f0/invoke-toolkit/pull/17)).
- [Field](../guides/fields.md) factories/resolvers are deferred during help/list/completion, but that does not defer unrelated import code ([PR #128](https://github.com/D3f0/invoke-toolkit/pull/128)).
- Completion callbacks are Python work too. Their thread wait timeout is not forced termination; cached candidates can be stale. See [completion](../humans/completion.md).
- Review PEP 723 metadata and dependencies: uv's isolated environment is not a sandbox for untrusted packages or task code.
- Rendered-output redaction does not remove secrets from process arguments, environment contents or every channel, and should not be generalized to native async execution. See [execution](../guides/execution.md).

Do not advertise a task file as safe to inspect merely because only `--list` or `--help` will be requested. Review and environment controls belong to the caller's workflow.

## Use changed listing as a review aid

For a Git-managed task file:

```sh
uv run intk --list-changed --list-format json
```

Or for the portable example:

```sh
uv run --script portable_tasks.py --list-changed --list-format json
```

`--list-changed` itself triggers a listing. It compares current task definitions with `HEAD`, combining staged and unstaged edits, and treats a new Git repository without commits as all-new tasks ([PR #146](https://github.com/D3f0/invoke-toolkit/pull/146)). JSON keeps the listing schema rather than adding a change-status field.

This is **not dependency-impact analysis**: imported tasks and indirect helper/global changes are excluded, as are formatting/comments. Historical source is parsed without executing it; current modules are still imported. An empty changed list does not prove every task's behavior is unchanged. Read the [full comparison boundary](../pep723/index.md#the-comparison-boundary) before using it to choose a test or execution scope.

## Author task interfaces for both audiences

- Describe behavior, prerequisites and side effects in task docstrings.
- Use [Enum/Literal/Annotated and path arguments](../guides/typed-arguments.md) for clear input contracts, but remember completion suggestions are not authorization.
- Document config dependencies and [Field](../guides/fields.md) resolution rather than hiding them in import-time work.
- Accept explicit noninteractive arguments before invoking [interactive selection](../humans/interactive-selection.md).
- Keep pre/post task output consistent with any JSON contract; Invoke chaining is not automatically concurrent execution.
- [Async tasks](../guides/async.md) are sequential by default; task code must request concurrency explicitly. Native async subprocess output is buffered and does not support PTY, watchers or sudo.

The repository includes an existing [invoke-toolkit task-authoring skill](https://github.com/D3f0/invoke-toolkit/blob/main/skills/invoke-toolkit-tasks/SKILL.md), introduced in [PR #110](https://github.com/D3f0/invoke-toolkit/pull/110). Read it as a reusable authoring aid, then confirm details against the installed library, task help and these source-aligned references; loading a skill does not install Toolkit or grant execution permission.

[Quickstart](../getting-started/quickstart.md) · [Human workflow](../humans/index.md) · [PEP 723](../pep723/index.md) · [CLI reference](../reference/cli.md) · [API reference](../reference/api.md) · [Troubleshooting](../reference/troubleshooting.md) · [Improvement history](../reference/improvements.md)
