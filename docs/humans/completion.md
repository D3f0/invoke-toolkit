# Autocompletion

Toolkit extends Invoke completion with typed choices, path markers, positional argument awareness and configuration-aware callbacks. Shell installation is a separate step from declaring completion behavior in Python.

## Install for bash, zsh or fish

Use a Toolkit CLI available as `intk` on your `PATH` ([installation](../getting-started/installation.md)). The exact built-in task namespace is **`shell`**; enable built-in collections with `-x`.

Choose your shell:

```sh
intk -x shell.install-completions --shell bash
```

```sh
intk -x shell.install-completions --shell zsh
```

```sh
intk -x shell.install-completions --shell fish
```

Or let the installer detect it from `$SHELL`:

```sh
intk -x shell.install-completions
```

An unrecognized or missing `$SHELL` requires an explicit `--shell`. The installer runs `intk --print-completion-script SHELL`, writes the generated file and, for bash/zsh, may append startup configuration ([PR #64](https://github.com/D3f0/invoke-toolkit/pull/64)).

| Shell | Installed file | Startup behavior |
| --- | --- | --- |
| bash | `~/.bashrc.d/intk.bash` | Adds a readable `*.bash` sourcing loop to `~/.bashrc` if not already configured |
| zsh | `~/.zfunc/_intk` | Adds `~/.zfunc` to `fpath` and initializes `compinit` in `~/.zshrc` if not already configured |
| fish | `~/.config/fish/completions/intk.fish` | fish discovers the file in a new session; no startup-file edit |

Restart the shell, or reload the matching startup file:

```bash
source ~/.bashrc
```

```zsh
source ~/.zshrc
```

For an already-running fish session:

```fish
source ~/.config/fish/completions/intk.fish
```

If your existing bash/zsh configuration already mentions the completion directory, the installer assumes it is configured. Check the actual sourcing loop or `fpath`/`compinit` setup if completion still does not load. zsh frameworks may already initialize `compinit`; keep a single intentional initialization in your startup configuration.

To install for Toolkit's other CLI name, use `--binary-name` with that executable on your `PATH`:

```sh
intk -x shell.install-completions --shell zsh --binary-name invoke-toolkit
```

This changes the installed filename and generator command; it is not an installer for arbitrary unrelated executables.

### Inspect and remove an installation

```sh
intk -x shell.completion-status
intk -x shell.uninstall-completions --shell bash
```

Status checks whether each completion file exists; it does not prove your shell has sourced it. Uninstall removes only the completion file and leaves the bash/zsh startup additions intact. Pass the same `--binary-name` used during installation when checking or removing a nondefault file.

If you prefer to manage startup configuration yourself, print the generator output:

```sh
intk --print-completion-script bash
intk --print-completion-script zsh
intk --print-completion-script fish
```

## What is completed

- Task names, aliases and flags, using the loaded collection.
- Built-in collection tasks when `-x` appears in the invocation ([PR #29](https://github.com/D3f0/invoke-toolkit/pull/29)).
- Enum and Literal values, dynamic Annotated callbacks and typed path markers ([PR #38](https://github.com/D3f0/invoke-toolkit/pull/38), [PR #41](https://github.com/D3f0/invoke-toolkit/pull/41)).
- Search-root directories and task collections selected through `-r` / `--search-root` ([PR #64](https://github.com/D3f0/invoke-toolkit/pull/64)).
- Positional arguments where a callback exists; a free-form positional argument does not fall back to irrelevant task names ([PR #53](https://github.com/D3f0/invoke-toolkit/pull/53)).
- Fish task descriptions without Rich markup, including nested tasks and quoted checkout paths ([PR #139](https://github.com/D3f0/invoke-toolkit/pull/139)).

Core flag and built-in completion can work without a `tasks.py`; absence of project tasks is not itself a completion error ([PR #65](https://github.com/D3f0/invoke-toolkit/pull/65)). Path-marker completion stays within the process's current working directory. This suggestion boundary does not sandbox task execution or restrict every explicit path argument; see [typed arguments](../guides/typed-arguments.md).

The generated scripts target CLI executables such as `intk`. They do not automatically install a dedicated shell wrapper for every `uv run --script FILE.py` invocation.

## Callbacks see loaded project configuration

[PR #94](https://github.com/D3f0/invoke-toolkit/pull/94) supplies a Toolkit context to callbacks; [PR #101](https://github.com/D3f0/invoke-toolkit/pull/101) forwards the program's **already-loaded configuration**, including project values. Use the two-argument callback contract `(ctx, incomplete) -> list[str]`.

Save this complete `tasks.py`:

```python
from typing import Annotated

from invoke_toolkit import Context, task


def complete_environments(ctx: Context, incomplete: str) -> list[str]:
    allowed = ctx.get_config_value(
        "deploy.allowed_envs", default=["development", "staging", "production"]
    )
    return sorted(name for name in allowed if name.startswith(incomplete))


@task
def choose(
    ctx: Context,
    environment: Annotated[str, "Environment name", complete_environments] = "staging",
) -> None:
    """Print an environment without deploying anything."""
    print(environment)
```

Add `invoke.yaml` alongside it:

```yaml
deploy:
  allowed_envs:
    - staging
    - production
completion:
  callback_timeout: 2.0
  disable_plugins: false
```

Run `intk choose --environment ` and press Tab. To request completion candidates directly without shell installation, from that directory:

```sh
intk --complete -- intk choose --environment
```

To execute the task explicitly:

```sh
intk choose --environment production
```

The callback provides **suggestions**, not validation: this string argument still accepts an explicitly supplied value outside the suggestion list. Use Enum/Literal or explicit task validation when allowed values must be enforced.

Callbacks should return candidates and avoid writing to stdout; stdout belongs to the completion protocol. Keep them read-only and fast. Modules are imported during completion, so top-level subprocesses, prompts and network calls still run; deferred [Field](../guides/fields.md) factories do not make module imports safe.

## Timeout is a wait limit, not cancellation

[PR #76](https://github.com/D3f0/invoke-toolkit/pull/76) adds a default **10-second** callback wait, configurable via `completion.callback_timeout` as above or the environment variable:

```sh
INVOKE_COMPLETION_CALLBACK_TIMEOUT=2.0 intk --complete -- intk choose --environment
```

The callback runs in a thread. If the wait expires, Toolkit stops waiting for its result and may fall through to other choice mechanisms, but it **does not terminate the callback thread**. A running callback can still delay process shutdown. This is not a hard shell-completion deadline or a sandbox; apply timeouts to network/subprocess work inside the callback itself.

## Cache expensive callback results

Install the optional cache dependency in the same environment as `intk`:

```sh
python -m pip install 'invoke-toolkit[cache]'
```

For a uv-managed project instead, use `uv add 'invoke-toolkit[cache]'` and run its CLI through `uv run intk`.

This complete `tasks.py` lists files in the current directory and caches candidates for 30 seconds:

```python
from pathlib import Path
from typing import Annotated

from invoke_toolkit import Context, cached, task


@cached(ttl=30)
def complete_files(ctx: Context, incomplete: str) -> list[str]:
    return sorted(
        path.name
        for path in Path.cwd().iterdir()
        if path.is_file() and path.name.startswith(incomplete)
    )


@task
def choose_file(
    ctx: Context,
    filename: Annotated[str, "File name", complete_files],
) -> None:
    """Print the selected name without reading the file."""
    print(filename)


@task
def clear_completions(ctx: Context) -> None:
    """Clear this callback's persisted results."""
    complete_files.cache_clear()
```

```sh
intk --complete -- intk choose-file --filename
intk clear-completions
```

`@cached()` defaults to a **300-second TTL**; the disk cache persists across completion processes. Without diskcache, the callback executes uncached. Keys use the callback's function name and incomplete string, not its context configuration or a source fingerprint: edits to config, files or callback code may leave stale suggestions until TTL expiration or `cache_clear()`. Use distinctive callback names and avoid caching configuration-sensitive data unless this tradeoff is acceptable.

`cache_info()` reports the backend and cache details. The optional `maxsize` is the diskcache size limit in **bytes**, not a count of candidate strings. This callback decorator is different from `@task(cache=...)`; see [caching](../guides/caching.md).

## Skip expensive plugins during completion only

[PR #144](https://github.com/D3f0/invoke-toolkit/pull/144) adds an opt-out for installed entry-point collection plugins during completion:

```yaml
completion:
  callback_timeout: 10.0
  disable_plugins: true
```

Or, in bash/zsh:

```sh
export INVOKE_COMPLETION_DISABLE_PLUGINS=1
```

In fish:

```fish
set -gx INVOKE_COMPLETION_DISABLE_PLUGINS 1
```

Project tasks, local tasks and built-in `-x` suggestions remain available. Normal task execution and listing still load plugins. The option does not prevent arbitrary imports in your own task modules.

## Record and share an autocompletion demo

**Recommended: asciinema for recording, asciinema player for browser replay.**
It records terminal output and timing, not a video of your desktop. A `.cast`
file preserves terminal text and control sequences, making it suitable for
showing completion menus, Rich colors, status panels and interactive selection.
Browser playback displays the recorded session; it does not execute its commands.

| Tool | Use it for | Tradeoff |
| --- | --- | --- |
| [asciinema + player](https://docs.asciinema.org/manual/player/quick-start/) | Capture a real session; browser playback with pause and seeking | A self-hosted page needs player JavaScript/CSS plus the `.cast` file |
| [agg](https://docs.asciinema.org/manual/agg/) | Convert the same recording to an animated GIF for a README | No interactive seeking or selectable terminal text |
| [VHS](https://github.com/charmbracelet/vhs) | Script a repeatable demo as a `.tape` file, including Tab presses | Runs commands again to render the demo; requires ttyd and ffmpeg |

### Capture the actual shell interaction

Install the recorder using the [asciinema installation guide](https://docs.asciinema.org/manual/cli/quick-start/).
Completion must already be installed and loaded in the shell being recorded.
For example, after setting up Fish completion:

```sh
asciinema rec --command fish --idle-time-limit 2 completion.cast
```

Use `--command 'bash -i'` or `--command 'zsh -i'` for an interactive Bash or Zsh
session. In the recorded shell, type `intk -x ` and press Tab. Then demonstrate
`intk choose --environment ` and press Tab, using the complete `choose` task
and `invoke.yaml` from [the callback example](#callbacks-see-loaded-project-configuration).
Select a suggested value and run the task. Type `exit` to finish recording.

To inspect the captured session locally:

```sh
asciinema play completion.cast
```

Use a consistent terminal size and short pauses. Terminal recording captures
what appears on screen, not the fact that a specific physical key was pressed:
the completion menu makes the effect of Tab visible. Avoid enabling input
capture merely to show Tab; `--capture-input` can also capture passwords.

### Replay in a browser

- **Hosted recording:** optionally run `asciinema upload completion.cast` to
  publish through an asciinema server. Follow the returned URL for browser
  playback. Uploading sends the recording to that service; it is not required
  for local recording or self-hosting.
- **GitHub Pages:** store the reviewed `.cast` file with the documentation
  assets and use the [standalone player integration](https://docs.asciinema.org/manual/player/quick-start/).
  Serve the player JavaScript/CSS locally, pin their release, and initialize
  the player only on pages containing a recording. Keep asset URLs compatible
  with the `/invoke-toolkit/` project prefix. This documentation recommends the
  integration; it does not currently bundle a player or a recording.
- **README preview:** after installing [agg](https://docs.asciinema.org/manual/agg/),
  convert a reviewed recording:

```sh
agg completion.cast completion.gif
```

Keep the `.cast` as the replayable original; the GIF is a presentation derivative.
For reproducible scripted screenshots or animations instead of a live session,
use VHS and its [Tab command](https://github.com/charmbracelet/vhs#vhs-command-reference).

!!! warning "Review recordings before sharing"

    Use a scratch project and non-secret example values. Output, echoed commands,
    prompts, paths and terminal metadata can disclose sensitive information even
    when input capture is disabled. Toolkit output redaction is not a recording
    sanitizer. Replay and inspect the recording before committing or uploading it;
    never record real credentials or rely on `hide=True` in a live status panel.

[Human workflow](index.md) · [Typed arguments](../guides/typed-arguments.md) · [Configuration](../guides/configuration.md) · [Troubleshooting](../reference/troubleshooting.md)
