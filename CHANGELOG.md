# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are generated automatically by [commitizen](https://commitizen-tools.github.io/commitizen/)
on version bumps.

---

## Unreleased
### Added

- Typed task `Field(default=...)` and `Field(default_factory=...)` values,
  including context-aware defaults and batched URI scheme resolution through
  the `invoke_toolkit.field_resolver` entry-point group.
- Resolver-only package scaffolding via
  `intk -x create.package --provider <scheme>`.
- `completion.disable_plugins: true` and `INVOKE_COMPLETION_DISABLE_PLUGINS=1`
  to omit installed entry-point plugins from shell completion without changing
  normal task discovery or execution.
- `--list-changed` to list new or updated task definitions compared with Git
  `HEAD`, including PEP 723 scripts; Rich highlights changes in normal flat and
  nested listings while keeping JSON output machine-readable.
- A Zensical documentation site for humans and AI agents, with a central PEP 723
  workflow, source-aligned library guides, CLI/API reference, and a complete
  merged-PR improvement index. GitHub Actions validates pull requests and
  deploys successful main builds to GitHub Pages after repository enablement.
- A prominent human autocompletion workflow and terminal-demo recording guide,
  recommending asciinema/browser playback with agg and VHS alternatives.


### Changed

- Replace the obsolete documentation generator and watcher tasks with
  `docs-build` and `docs-preview`; refresh README highlights and contributor
  instructions. Documentation tooling requires Python 3.11+, independently of
  the library's unchanged Python 3.10+ support.
- Separate CI runner and test dependencies from developer and documentation
  tooling; GitHub Actions installs only Nox, and each Python session installs
  the dedicated test group using the committed lockfile.

### Fixed

- Preserve carriage-return bytes when forwarding terminal input to interactive
  subprocesses launched with `pty=True`, so Enter behaves like direct execution.
- Avoid importing Copier and its dependency tree while completing built-in
  `-x` tasks; Copier now loads only when `create.package` executes.

### Security

- Authenticate task and completion cache values with a private, machine-local
  HMAC-SHA256 key before unpickling. Reject unsigned legacy values, serialized
  keys, file-backed entries and tampered payloads; preserve Python-object
  results and recompute cache misses. Disable caching if key storage is unsafe.
  This mitigates DiskCache's unpatched GHSA-w8v5-vhqr-4h9v in toolkit cache readers.
- Include the cache authentication backend in source control and built packages;
  prevent the scratch-file ignore rule from omitting it in fresh checkouts.
- Require AnyIO >=4.14.2 for runtime TLS fixes. Update locked Black, FileLock,
  urllib3, uv and virtualenv to patched releases, with security version floors.
  Development and CI groups now require Python >=3.11 for patched FileLock;
  Python 3.10 remains supported for runtime installation.

### Breaking Changes

- **invoke 3.0.x compatibility** — minimum required invoke version bumped from
  `>=2.2.1` to `>=3.0.3`. invoke 3.0 introduced a backwards-incompatible
  change to `Call.make_context` (new required `core_parse_result` argument) and
  a new `Context.remainder` attribute. The following internal components were
  updated to match:

  - `ToolkitCall.make_context` now accepts `core_parse_result: ParseResult`
    and forwards `core_parse_result.remainder` into `ToolkitContext`.
  - `ToolkitContext.__init__` now accepts `remainder: str = ""` and passes it
    to `invoke.context.Context.__init__`, making `ctx.remainder` available
    inside tasks for wrapper-task patterns (e.g. `c.run(f"docker … {c.remainder}")`).
  - `ToolkitExecutor.__init__` now defaults `self.core` to `ParseResult()`
    instead of `None`, matching upstream `Executor` behaviour and ensuring
    `core_parse_result.remainder` is always safe to access.

### What invoke 3.0 brings

- `Context.remainder` — exposes the CLI parser's remainder string (text after
  a standalone `--`) directly on the context object, enabling elegant
  [wrapper tasks](https://docs.pyinvoke.org/en/latest/concepts/invoking-tasks.html#wrapper-tasks).
- `run()` return type — `Result` instead of `Optional[Result]`; `disown=True`
  now returns `Result(disowned=True)` instead of `None`.
- `Promise` is now a subclass of `Result` and gains a `__repr__`.

### References

- invoke 3.0.0 changelog: <https://www.pyinvoke.org/changelog.html#3-0-0-2026-04-05>
- Fabric reference fix: <https://github.com/fabric/fabric/commit/7fa309db9dd5dac69079c1fb83b6f579555f7d53>
