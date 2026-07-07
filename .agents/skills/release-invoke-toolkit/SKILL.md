---
name: release-invoke-toolkit
description: >
  Create a new release for invoke-toolkit by comparing the latest PyPI version against
  main, proposing a version bump, and creating a GitHub Release (CI handles the wheel
  build and PyPI publish automatically). Use when the user says "cut a release",
  "ship a new version", "create release", "bump and release", "what's unreleased",
  "release patch/minor/major", or anything that implies tagging + publishing the package.
allowed-tools: Bash(git *) Bash(gh *) Bash(curl *) Bash(python *)
---

# invoke-toolkit Release Workflow

## When to use

- User asks to "cut a release", "ship a new version", "create a release", "bump the version"
- User asks "what's unreleased?" or "what's changed since last release?"
- User wants to tag + publish a new version of `invoke-toolkit` to PyPI and GitHub

## When NOT to use

- The user only wants to build the package locally (use `inv build` instead)
- The user wants to publish to PyPI directly without creating a GitHub Release
- The repository is not `D3f0/invoke-toolkit` / `work.github.com:D3f0/invoke-toolkit`

---

## How releases work

Creating a GitHub Release is the **only manual step** needed. The rest is automated:

```
gh release create v<next>        ← you do this
        │
        └─► publish-releases.yaml fires (on: release published)
                ├─ Runs nox test suite
                └─ Builds wheel (hatchling + uv-dynamic-versioning)
                        └─► Publishes to PyPI via OIDC trusted publishing
```

There is also a CI path (`test-release-and-publish.yaml`) that triggers on push/merge
to `main` when the commit message contains `[release patch/minor/major]`, but the
direct `gh release create` approach is simpler and more explicit.

**No wheel upload is needed** — CI builds and publishes the wheel after the release is
created. Do not pass local `.whl` files to `gh release create`.

---

## Workflow

### 1. Check the current published version (PyPI)

Fetch the latest version published to PyPI:

```bash
curl -s https://pypi.org/pypi/invoke-toolkit/json | python -c \
  "import sys, json; d=json.load(sys.stdin); print(d['info']['version'])"
```

Save this as `PYPI_VERSION` (e.g. `0.0.61`).

### 2. Find the matching git tag

```bash
git fetch --tags
git tag --sort=-version:refname | head -5
```

The latest tag should match `v<PYPI_VERSION>`. If they diverge (e.g. the latest tag is
ahead of PyPI), note this — the tag is the ground truth for "what's released".
Use the latest tag as `CURRENT_TAG`.

### 3. Compare tag..HEAD (unreleased commits)

```bash
git log <CURRENT_TAG>..HEAD --oneline
```

Display this list to the user. If there are **no commits**, tell the user there is
nothing to release and stop.

### 4. Propose the next version

Parse the commit list and infer the bump type using conventional commit prefixes:

| Commit contains | Bump |
|----------------|------|
| `BREAKING CHANGE` in body, or `!` after type (e.g. `feat!:`) | **major** |
| `feat:` or `feat(<scope>):` | **minor** |
| anything else (`fix:`, `chore:`, `refactor:`, `docs:`, etc.) | **patch** |

**Default to `patch`** when there are no conventional commit prefixes.

Current tag `vX.Y.Z` → next tag based on bump:
- patch → `vX.Y.(Z+1)`
- minor → `vX.(Y+1).0`
- major → `v(X+1).0.0`

Present the proposed next tag and bump type to the user with the commit list as
justification. **Wait for explicit user confirmation before proceeding.**

> Example message to user:
> "Based on the commits since `v0.0.61`, I propose a **patch** bump → `v0.0.62`.
> Changes: [list]. Shall I proceed?"

If the user wants a different version, use their value.

### 5. Pre-flight safety checks

Before tagging, verify:

```bash
# Must be on main (or the branch the user intends to release from)
git rev-parse --abbrev-ref HEAD

# Working tree must be clean
git status --porcelain

# Tag must not already exist
git tag -l "v<NEXT>"
```

- If not on `main`: warn the user and ask for confirmation to proceed anyway.
- If working tree is dirty: stop and tell the user to commit or stash changes first.
- If the tag already exists: stop — do not overwrite an existing tag.

### 6. Create the GitHub Release (with --generate-notes)

```bash
gh release create v<NEXT> \
  --title "v<NEXT>" \
  --generate-notes \
  --draft
```

Use `--draft` first so the release body can be reviewed and enhanced before
it goes live (which would immediately trigger the publish CI).

Capture the auto-generated notes body:

```bash
gh release view v<NEXT> --json body --jq '.body'
```

### 7. Enhance the release notes with an AI summary

Read the auto-generated "What's Changed" notes, then prepend an AI-written
introduction paragraph that covers:

- The **overall intent** of this release (what problem it solves or what area it improves)
- Any **new user-facing functionality** (new tasks, new APIs, new CLI flags)
- Any **notable fixes** that users should be aware of

Format for the enhanced body:
```markdown
<AI-written intro paragraph here>

## What's Changed
<auto-generated PR list from --generate-notes>

**Full Changelog**: <auto-generated link>
```

Apply the enhanced notes:

```bash
gh release edit v<NEXT> --notes "<enhanced body>"
```

### 8. Publish the release (triggers CI)

Once the notes look good, publish the draft release:

```bash
gh release edit v<NEXT> --draft=false
```

This immediately triggers `publish-releases.yaml`.

### 9. Monitor CI and announce

```bash
# Watch for the publish workflow run
gh run list --workflow publish-releases.yaml --limit 3

# Wait for it to complete (optional; will stream output)
gh run watch
```

Once the workflow succeeds, confirm publication:

```bash
curl -s https://pypi.org/pypi/invoke-toolkit/json | python -c \
  "import sys, json; d=json.load(sys.stdin); print(d['info']['version'])"
```

Report back to the user:
- ✅ GitHub Release URL: `https://github.com/D3f0/invoke-toolkit/releases/tag/v<NEXT>`
- ✅ PyPI URL: `https://pypi.org/project/invoke-toolkit/<NEXT>/`

---

## Safeguards

| Situation | Action |
|-----------|--------|
| No commits since last tag | Stop. Tell user there is nothing to release. |
| Dirty working tree | Stop. Ask user to commit or stash first. |
| Tag already exists locally or remotely | Stop. Do not proceed — never force-push or delete a release tag. |
| Not on `main` | Warn the user; ask for explicit confirmation before proceeding. |
| PyPI version > latest git tag | Investigate — this should not happen. Report to user. |
| CI publish run fails | Do NOT retry manually. Check the run logs via `gh run view <run-id>`. |

---

## Rollback / Undo

If the release was created by mistake **before** the CI publish run completes:

```bash
# Delete the GitHub Release (this does NOT push to PyPI yet if CI hasn't finished)
gh release delete v<NEXT> --yes

# Delete the git tag locally and remotely
git tag -d v<NEXT>
git push origin --delete v<NEXT>
```

**Once a version has been published to PyPI it cannot be fully undone.** PyPI allows
yanking a release (`pip install` will skip it by default) but the files remain:

```bash
# Yank from PyPI (requires PyPI API token / trusted publishing environment)
# This is a last resort — contact the maintainer to yank via the PyPI UI.
```

If only the release notes need fixing after publish:

```bash
gh release edit v<NEXT> --notes "<corrected body>"
```
