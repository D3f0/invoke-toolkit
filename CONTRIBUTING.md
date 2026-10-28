# Contributing to invoke-toolkit

This document provides guidelines and information about our development workflow.

## Documentation

The documentation is Markdown in `docs/`, built with Zensical. Keep examples
runnable and link canonical guides rather than duplicating feature manuals.
Runtime support remains Python 3.10+; documentation tooling needs Python 3.11+.

```console
uv sync --python 3.13 --group doc
uv run --group doc intk docs-build
uv run --group doc intk docs-preview
```

The build uses strict internal-link and anchor validation. Preview serves the
site locally with live reload. Edit `zensical.toml` when adding navigation pages;
keep PEP 723 between the human and AI-agent entrypoints. Update the
[improvement index](docs/reference/improvements.md) when documenting merged
features. The checked-in `uv.lock` pins the generator and dependencies.

### GitHub Pages

`.github/workflows/docs.yaml` builds every pull request and push to `main`.
Only successful `main` builds, including manual runs on `main`, upload and deploy
a Pages artifact. Pull requests never receive deployment permissions.

Before the first deployment, a repository administrator must select
**Settings → Pages → Build and deployment → Source → GitHub Actions** and enable
the site. Keep the `github-pages` environment's deployment policy restricted to
`main`. The expected project URL is
<https://d3f0.github.io/invoke-toolkit/>; there is no generated source branch to
maintain. The workflow does not enable Pages automatically or require a personal
access token.

## Release Workflow

Our project uses an automated release process triggered by specific keywords in commit messages and pull request titles.

### Automatic Version Bumping

The project automatically creates releases when a commit or merged pull request contains one of the following keywords:

- `[release major]` or `[bump major]` - Bumps the major version (e.g., 1.0.0 → 2.0.0)
- `[release minor]` or `[bump minor]` - Bumps the minor version (e.g., 1.0.0 → 1.1.0)
- `[release patch]` or `[bump patch]` - Bumps the patch version (e.g., 1.0.0 → 1.0.1)

### How It Works

1. **Direct Commits to main**: When you push a commit to the main branch with one of the keywords in the commit message, the release workflow is triggered.

2. **Merged Pull Requests**: When a pull request with one of the keywords in its title or description is merged to main, the release workflow is triggered.

3. **Automated Release**: Once triggered, the workflow:
   - Creates and pushes a new version tag
   - Creates a GitHub Release with the new version
   - Publishes the package to PyPI

### Example Usage

**In a commit message:**
```
git commit -m "Fix critical bug [release patch]"
```

**In a pull request title:**
- Title: "Add new feature [bump minor]"
- Description can also contain the keyword

### Testing

To run the test suite locally:
```bash
uv run pytest
```

You can run specific tests by providing the file path or using the `-k` flag:
```bash
uv run pytest tests/test_specific.py
uv run pytest -k test_name
```

### Development Setup

This project uses `uv` for dependency management. To make package modifications:
```bash
uv add package-name
uv remove package-name
```

### Pre-commit Hooks

This project uses pre-commit hooks to maintain code quality. To set up the hooks using `uvx`:

```bash
uvx pre-commit install
```

This will automatically run checks on staged files before each commit, including:
- Linting and formatting with Ruff
- Secret detection
- Spell checking
- YAML validation
- Trailing whitespace removal

To manually run the pre-commit hooks on all files:
```bash
uvx pre-commit run --all-files
```

## Code Style

Please follow the existing code style and comment conventions in the project. Make minimal modifications focused on the specific changes you're implementing.
