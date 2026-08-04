# Plan: Create a New Release

## Context

The project has **two release mechanisms** today:

| Mechanism | Where | How |
|---|---|---|
| `release` task (`tasks.py`) | local CLI | Interactive: proposes next patch tag, creates it, pushes, calls `gh release create` |
| CI release workflow | `.github/workflows/` | Keyword-triggered (`[release patch/minor/major]` in commit/PR) — creates tag + GH release + publishes to PyPI |

The **current local `release` task** is functional but has a few gaps:
- Only proposes a patch bump; other bump types require manual input
- Does not generate/display release notes
- Does not handle `[release minor]` / `[release major]` as shortcuts
- Calls `subprocess.run` for the `gh` step instead of `ctx.run`

The goal is to **improve the existing `release` task** so it's easier, safer, and aligned with the CI convention.

## Approach

Update the `release` task in `tasks.py` to:

1. Let the user choose the bump type (patch / minor / major) via a `bump` parameter (Literal / Enum)
2. Auto-compute the next version for each bump type (patch already done; add minor/major)
3. Show a preview of commits since the last tag (release notes draft)
4. Prompt for confirmation once, then execute
5. Use `ctx.run` consistently (replace bare `subprocess.run`)
6. Add a `--dry-run` flag for safe local testing

## Files to Modify

- `tasks.py` — only the `release` task function needs to be updated (lines ~90–145)

## Reuse

| Existing code | Location | Used for |
|---|---|---|
| `clean(ctx)` | `tasks.py` | Pre-release clean (already called) |
| `build(ctx, target_="wheel")` | `tasks.py` | Build wheel (already called) |
| `ctx.run(...)` | ToolkitContext | Replace bare `subprocess.run` for `gh release create` |
| `ctx.print(...)` | ToolkitContext | Rich output |
| `Prompt.ask` / `rich.prompt` | already imported | Confirm prompt |
| `Annotated`, `Literal` | already imported | Typed bump parameter |

## Steps

- [ ] Add `bump` parameter typed as `Literal["patch", "minor", "major"]` defaulting to `"patch"`
- [ ] Refactor version-computation logic to handle all three bump types
- [ ] Build release notes from `git log vPREV..HEAD --oneline` and display them before confirming
- [ ] Rename confirmation prompt to be clearer; keep Ctrl-C / Ctrl-D cancellation
- [ ] Replace `subprocess.run(..., shell=True, check=True)` with `ctx.run(...)` for the `gh` call, passing release notes via `--notes "..."`
- [ ] Add `dry_run: bool = False` flag — skips tag push, build, and `gh release create`
- [ ] Add `Annotated` help strings to all parameters

## Verification

```bash
# Dry-run to confirm logic without side effects
inv release --dry-run

# Dry-run a minor bump
inv release --bump minor --dry-run

# Check help text
inv --help release
```

---

## Decisions

1. **Release notes** — generate from `git log vPREV..HEAD --oneline` and pass via `gh release create --notes "..."`
2. **Tag push** — keep direct tag creation + push (bypass CI keyword flow)
3. **Pre-release** — not supported
