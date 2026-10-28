# Improvements over Invoke

Invoke Toolkit retains Invoke's Python task functions, contexts, pre/post tasks, aliases, command execution and task chaining. These are not new Toolkit features. Toolkit adds the following library and terminal improvements.

## Feature map

| Improvement | What changes | Guide |
| --- | --- | --- |
| Terminal ergonomics | Rich output, status/live command panels, process titles | [Rich output](../humans/rich-output.md) |
| Completion and selection | Typed choices/paths, config-aware callbacks, cache/timeouts, Bash/Zsh/Fish, fzf | [Completion](../humans/completion.md), [selection](../humans/interactive-selection.md) |
| Portable automation | PEP 723 dependency declarations and direct task-script execution with uv | [PEP 723](../pep723/index.md) |
| Agent discovery | JSON listings, scoped lists, changed task definitions, authoring skill | [AI agents](../agents/index.md) |
| Typed task inputs | Enum/Literal/path conversion and validation, Annotated help/callbacks | [Typed arguments](../guides/typed-arguments.md) |
| Shared automation | Local collections, package discovery, entry-point plugins, uv plugin lifecycle | [Collections](../guides/collections.md), [plugins](../guides/plugins.md) |
| Configuration | Dot-path tools and attrs/cattrs schemas | [Configuration](../guides/configuration.md) |
| Dynamic values | Context-aware factories, batched URI text resolvers, managed temporary path files | [Fields](../guides/fields.md) |
| Reused results | Optional persistent task-result caching, TTL and argument-key controls | [Caching](../guides/caching.md) |
| I/O concurrency | Coroutine task bodies and explicit async subprocess/gather APIs | [Async](../guides/async.md) |
| Execution utilities | Limited synchronous output redaction and temporary process titles | [Execution](../guides/execution.md) |
| Packaging | Copier templates, short names, configuration overrides and provider packages | [Packages](../guides/packages.md) |

## Complete merged-PR coverage

This index covers **all 65 merged pull requests through #149**, at source baseline [`b60d09a`](https://github.com/D3f0/invoke-toolkit/tree/b60d09a). Each row links the originating PR and its current guide. Related fixes are sections within the same guide rather than duplicate manuals. Guide examples follow current source, not stale historical PR snippets.

CI, dependency and release-maintenance changes are retained as maintenance, not claimed as new library APIs. #22 is an autoprint regression test; #44 adds a dependency, not an HTTP client abstraction. The generated package's Python requirement is separate from the library's Python >=3.10 requirement. Invoke 3 compatibility (#114) exposes upstream functionality; it does not mean Toolkit invented wrapper tasks.

| Merged PR | Current improvement or maintenance scope | Documentation |
| --- | --- | --- |
| [#149: fix: update certifi past compromised CA range](https://github.com/D3f0/invoke-toolkit/pull/149) | Maintenance: certifi security update | [Maintainer notes](#maintainer-notes) |
| [#148: fix: include cache authentication backend in fresh checkouts](https://github.com/D3f0/invoke-toolkit/pull/148) | Authenticated cache backend distributed in fresh checkouts | [Guide](../guides/caching.md#authenticated-cache-storage) |
| [#147: security: authenticate cache values with HMAC-SHA256 before unpickling](https://github.com/D3f0/invoke-toolkit/pull/147) | Cache authentication, safe dependency quoting and security dependency floors | [Guide](../guides/caching.md#authenticated-cache-storage) |
| [#146: feat: list and highlight Git-changed task definitions [release patch]](https://github.com/D3f0/invoke-toolkit/pull/146) | Git-changed task listing and Rich highlights | [Guide](../pep723/index.md) |
| [#144: perf: speed up shell completion](https://github.com/D3f0/invoke-toolkit/pull/144) | Faster completion; skip installed plugins during completion only | [Guide](../humans/completion.md) |
| [#142: fix: preserve Enter in PTY subprocesses](https://github.com/D3f0/invoke-toolkit/pull/142) | PTY Enter forwarding and terminal restoration fixes | [Guide](../guides/execution.md) |
| [#140: feat: suggest similar task and collection names](https://github.com/D3f0/invoke-toolkit/pull/140) | Similar task, alias and collection-name suggestions | [Guide](troubleshooting.md) |
| [#139: feat: improve fish completion support](https://github.com/D3f0/invoke-toolkit/pull/139) | Fish descriptions, nested and quoted-path completion | [Guide](../humans/completion.md) |
| [#138: feat: manage uv tool plugin lifecycle](https://github.com/D3f0/invoke-toolkit/pull/138) | Persistent uv tool plugin lifecycle | [Guide](../guides/plugins.md) |
| [#137: fix: handle macOS PTY stdin buffer overflow](https://github.com/D3f0/invoke-toolkit/pull/137) | macOS PTY stdin buffer handling fix | [Guide](../guides/execution.md) |
| [#135: fix: validate release tags before publishing](https://github.com/D3f0/invoke-toolkit/pull/135) | Maintenance: validated release tags before publication | [Maintainer notes](#maintainer-notes) |
| [#133: fix: prefer main local task namespace](https://github.com/D3f0/invoke-toolkit/pull/133) | Primary local namespace wins over local_tasks.py | [Guide](../guides/collections.md) |
| [#131: chore(deps): bump uv from 0.9.7 to 0.11.15](https://github.com/D3f0/invoke-toolkit/pull/131) | Maintenance: uv dependency update | [Maintainer notes](#maintainer-notes) |
| [#130: ci: harden GitHub Actions supply chain](https://github.com/D3f0/invoke-toolkit/pull/130) | Maintenance: pinned Actions and release-workflow supply chain | [Maintainer notes](#maintainer-notes) |
| [#128: feat: add dynamic task fields and URI providers](https://github.com/D3f0/invoke-toolkit/pull/128) | Dynamic Fields, URI text resolvers and provider packages | [Guide](../guides/fields.md) |
| [#127: fix: address async task regressions](https://github.com/D3f0/invoke-toolkit/pull/127) | Async hide behavior, mixed sync graphs and grouped tasks | [Guide](../guides/async.md) |
| [#123: fix: avoid local task module collisions](https://github.com/D3f0/invoke-toolkit/pull/123) | Path-isolated local task module discovery | [Guide](../guides/collections.md) |
| [#121: feat: add async task support](https://github.com/D3f0/invoke-toolkit/pull/121) | Coroutine tasks, native async commands and gather | [Guide](../guides/async.md) |
| [#120: feat: add --list-tasks and --list-plugins filter flags](https://github.com/D3f0/invoke-toolkit/pull/120) | Separate primary-task and plugin listings | [Guide](cli.md) |
| [#118: fix: prevent CI hangs from -s flag and unguarded subprocess in proctitle test](https://github.com/D3f0/invoke-toolkit/pull/118) | Maintenance: prevent CI test subprocess hangs | [Maintainer notes](#maintainer-notes) |
| [#116: fix: warn and strip self-referential aliases to prevent RecursionError](https://github.com/D3f0/invoke-toolkit/pull/116) | Self-referential aliases warned and removed | [Guide](troubleshooting.md) |
| [#114: feat!: compatibility with invoke 3.0.3](https://github.com/D3f0/invoke-toolkit/pull/114) | Invoke >=3.0.3 compatibility; inherited remainder forwarding | [Guide](../getting-started/from-invoke.md) |
| [#112: feat: updated pyproject.toml PyPI metadata and add release skill](https://github.com/D3f0/invoke-toolkit/pull/112) | Packaging metadata, typed marker and release-authoring skill | [Guide](api.md) |
| [#110: feat: add skills/ folder with invoke-toolkit-tasks skill](https://github.com/D3f0/invoke-toolkit/pull/110) | Task-authoring skill for AI agents | [Guide](../agents/index.md) |
| [#108: ci: fix missing workflow permissions for CodeQL](https://github.com/D3f0/invoke-toolkit/pull/108) | Maintenance: explicit CodeQL workflow permissions | [Maintainer notes](#maintainer-notes) |
| [#107: chore(deps): update black and urllib3 to fix high severity vulnerabilities](https://github.com/D3f0/invoke-toolkit/pull/107) | Maintenance: security dependency updates | [Maintainer notes](#maintainer-notes) |
| [#105: feat: show command output below status spinner](https://github.com/D3f0/invoke-toolkit/pull/105) | Recent command output below Rich status spinners | [Guide](../humans/rich-output.md) |
| [#104: fix(#39): script() now loads project config when using PEP723 mode](https://github.com/D3f0/invoke-toolkit/pull/104) | Project configuration loaded for script() | [Guide](../pep723/index.md) |
| [#101: feat: thread loaded config into completion callbacks (closes #95)](https://github.com/D3f0/invoke-toolkit/pull/101) | Loaded project configuration in completion callbacks | [Guide](../humans/completion.md) |
| [#100: feat(create): fix collection name and Python version in package template](https://github.com/D3f0/invoke-toolkit/pull/100) | Generated collection names, Python requirement and versioning | [Guide](../guides/packages.md) |
| [#94: feat: add ctx.get_config_value() method and fix completion config](https://github.com/D3f0/invoke-toolkit/pull/94) | Context dot-path config lookup and callback context | [Guide](../guides/configuration.md) |
| [#93: feat: Add config.unset command](https://github.com/D3f0/invoke-toolkit/pull/93) | Configuration unset command | [Guide](../guides/configuration.md) |
| [#90: feat: Add attrs-based config schemas with validation](https://github.com/D3f0/invoke-toolkit/pull/90) | attrs-based config schemas and validation | [Guide](../guides/configuration.md) |
| [#83: feat: use ctx.print_err for fzf fallback messages](https://github.com/D3f0/invoke-toolkit/pull/83) | fzf fallback diagnostics on stderr | [Guide](../humans/interactive-selection.md) |
| [#82: refactor: simplify config access in fzf module](https://github.com/D3f0/invoke-toolkit/pull/82) | Maintenance: simpler fzf config access | [Guide](../humans/interactive-selection.md) |
| [#81: fix: properly quote fzf arguments containing spaces](https://github.com/D3f0/invoke-toolkit/pull/81) | fzf option values with spaces quoted | [Guide](../humans/interactive-selection.md) |
| [#80: feat: add fzf integration for interactive selection with rich fallback](https://github.com/D3f0/invoke-toolkit/pull/80) | fzf selection with reduced Rich fallback | [Guide](../humans/interactive-selection.md) |
| [#76: Add timeout and persistent caching for completion callbacks](https://github.com/D3f0/invoke-toolkit/pull/76) | Completion callback timeout and persistent cache | [Guide](../humans/completion.md) |
| [#71: fix: restore config.set positional arguments without --path and --value flags](https://github.com/D3f0/invoke-toolkit/pull/71) | Historical positional config.set repair; current syntax in guide | [Guide](../guides/configuration.md) |
| [#65: feat: Fix completion issues and improve config.set](https://github.com/D3f0/invoke-toolkit/pull/65) | Completion without task files; config set handling | [Guide](../humans/completion.md) |
| [#64: feat: Fix completion with -r flag and add shell completion installer](https://github.com/D3f0/invoke-toolkit/pull/64) | Search-root completion and shell completion installer | [Guide](../humans/completion.md) |
| [#62: Fix basedpyright partially unknown type warnings for ctx.print and ctx.cd](https://github.com/D3f0/invoke-toolkit/pull/62) | Maintenance: context print/cd typing improvements | [Guide](api.md) |
| [#53: feat: suppress task name completion when completing positional args](https://github.com/D3f0/invoke-toolkit/pull/53) | Suppress unrelated task suggestions for positional values | [Guide](../humans/completion.md) |
| [#52: feat: add config.get and config.set tasks with completion and type validation](https://github.com/D3f0/invoke-toolkit/pull/52) | Config get/set, formats, locations and validation | [Guide](../guides/configuration.md) |
| [#51: feat: add cache parameter to @task decorator](https://github.com/D3f0/invoke-toolkit/pull/51) | Optional task-result cache with TTL and cache controls | [Guide](../guides/caching.md) |
| [#50: feat: add proctitle support for setting process title](https://github.com/D3f0/invoke-toolkit/pull/50) | Task and context process titles | [Guide](../guides/execution.md) |
| [#48: feat: add git configurable template endpoint for create.package](https://github.com/D3f0/invoke-toolkit/pull/48) | Git-configurable Copier template source | [Guide](../guides/packages.md) |
| [#44: Add httpx](https://github.com/D3f0/invoke-toolkit/pull/44) | Maintenance: httpx dependency only, no new HTTP API | [Maintainer notes](#maintainer-notes) |
| [#41: extend invoke completion](https://github.com/D3f0/invoke-toolkit/pull/41) | Typed choices, callbacks and path-aware completion | [Guide](../guides/typed-arguments.md) |
| [#38: feat: add enum arguments support to tasks (#37)](https://github.com/D3f0/invoke-toolkit/pull/38) | Enum, Literal and optional/union CLI conversion | [Guide](../guides/typed-arguments.md) |
| [#36: fix: handle Path objects in autoprint without line breaks](https://github.com/D3f0/invoke-toolkit/pull/36) | Path result autoprint without unwanted line breaks | [Guide](../humans/rich-output.md) |
| [#34: fix: add ext-name parameter and git repo check to package creation](https://github.com/D3f0/invoke-toolkit/pull/34) | Short extension names and Git-repository creation guard | [Guide](../guides/packages.md) |
| [#33: feat: extensions short names](https://github.com/D3f0/invoke-toolkit/pull/33) | Plugin short collection names and duplicate warnings | [Guide](../guides/plugins.md) |
| [#31: Plugin Support with Flat Task Discovery](https://github.com/D3f0/invoke-toolkit/pull/31) | Entry-point plugins and flat package task discovery | [Guide](../guides/collections.md) |
| [#30: fix: implement redaction for subprocess output in ctx.run()](https://github.com/D3f0/invoke-toolkit/pull/30) | Synchronous subprocess output redaction | [Guide](../guides/execution.md) |
| [#29: Enable autocompletion for -x flag with internal collections](https://github.com/D3f0/invoke-toolkit/pull/29) | Built-in -x task completion | [Guide](../humans/completion.md) |
| [#27: rich minimal version 13](https://github.com/D3f0/invoke-toolkit/pull/27) | Maintenance: Rich minimum version | [Maintainer notes](#maintainer-notes) |
| [#25: Add flag to respect $SHELL, add short-hand for disable-status and tests](https://github.com/D3f0/invoke-toolkit/pull/25) | SHELL initialization and status suppression shorthand | [Guide](../humans/rich-output.md) |
| [#22: Closes #9](https://github.com/D3f0/invoke-toolkit/pull/22) | Regression coverage: long-string autoprint remains one line | [Guide](../humans/rich-output.md) |
| [#21: local_tasks.py support](https://github.com/D3f0/invoke-toolkit/pull/21) | local_tasks.py discovery in local namespace | [Guide](../guides/collections.md) |
| [#19: Disable status](https://github.com/D3f0/invoke-toolkit/pull/19) | Rich status suppression | [Guide](../humans/rich-output.md) |
| [#17: Exit script() when load_collection is detected [bump patch]](https://github.com/D3f0/invoke-toolkit/pull/17) | Prevent duplicate script() task execution on collection load | [Guide](../pep723/index.md) |
| [#13: Make global context available for scripts](https://github.com/D3f0/invoke-toolkit/pull/13) | Global Context/run/sudo for scripts and REPLs | [Guide](api.md) |
| [#11: feat: Add get_config_value helper and config_prefix support for script()](https://github.com/D3f0/invoke-toolkit/pull/11) | Config dot-path lookup and custom script config prefix | [Guide](../guides/configuration.md) |
| [#8: Initial support for packages](https://github.com/D3f0/invoke-toolkit/pull/8) | Copier task-package generation | [Guide](../guides/packages.md) |

## Maintainer notes

Workflow permissions and immutable Action pins (#108, #130), release tag validation (#135), CI subprocess cleanup (#118), dependency updates (#27, #44, #107, #131), and packaging/type metadata (#62, #112) improve maintainability and distribution. They are not additional task execution modes. See the [contribution and release workflow](https://github.com/D3f0/invoke-toolkit/blob/main/CONTRIBUTING.md) and [changelog](https://github.com/D3f0/invoke-toolkit/blob/main/CHANGELOG.md).

The Pages workflow builds documentation on pull requests and deploys successful `main` builds with narrowly scoped permissions. A repository administrator must first enable GitHub Pages with Actions as its source. Documentation is built with [Zensical](https://zensical.org/docs/); its landing and navigation follow the progressive-disclosure pattern of [marimo's documentation](https://docs.marimo.io/), without borrowing marimo's product claims.
