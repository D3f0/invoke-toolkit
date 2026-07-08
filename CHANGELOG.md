# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Entries are generated automatically by [commitizen](https://commitizen-tools.github.io/commitizen/)
on version bumps.

---

## Unreleased

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
