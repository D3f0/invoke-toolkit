# Creating reusable packages

Toolkit's built-in `create.package` uses Copier to generate a task collection package or a resolver-only Field provider. The generated package is Python source you own; generation does not install it in every consumer environment or publish it to PyPI.

Origins: initial package generation [#8](https://github.com/D3f0/invoke-toolkit/pull/8), entry points [#31](https://github.com/D3f0/invoke-toolkit/pull/31), naming/safety [#34](https://github.com/D3f0/invoke-toolkit/pull/34).

## Prerequisites and creation

Install the optional Copier extra in the environment whose `intk` will create packages. Use Python 3.11 or newer for generated packages; Toolkit's own runtime supports Python 3.10+, but the bundled generated template has a Python 3.11 minimum.

```bash
python -m pip install 'invoke-toolkit[copier]'
```

Choose an existing writable parent directory **outside any Git repository**. The command refuses a target parent inside a detected Git repo and a target directory that already exists. The following POSIX example creates a fresh parent with `mktemp`:

```bash
package_parent=$(mktemp -d)
intk -x create.package --ext-name docs-demo --location "$package_parent"
uv sync --directory "$package_parent/invoke-toolkit-docs-demo"
uv run --directory "$package_parent/invoke-toolkit-docs-demo" intk --list
uv run --directory "$package_parent/invoke-toolkit-docs-demo" intk docs-demo.hello
```

This uses [uv](https://docs.astral.sh/uv/) for the generated project's environment. Keep the created directory if you want to develop it; no automatic cleanup or deletion is performed. The package exposes a collection through the `invoke_toolkit.collection` entry-point group and uses **flat** submodule task discovery by default, so `tasks.hello` becomes `docs-demo.hello`.

`--ext-name docs-demo` produces distribution/directory `invoke-toolkit-docs-demo`, import package `invoke_toolkit_docs_demo` and collection `docs-demo`. It determines the actual package name even if `--name` is also given. Without `--ext-name`, `--name my-tasks` uses that distribution name and an underscore-normalized module/collection name. When the full name starts `invoke-toolkit-`, the template strips that prefix for the collection. Keep names valid for Python packaging; do not infer universal normalization/validation for arbitrary names.

Current templates generate static version `0.1.0`, Hatchling metadata and Python `>=3.11` ([#100](https://github.com/D3f0/invoke-toolkit/pull/100)). To switch flat to nested module names, use `collection.add_collections_from_namespace(...)` in the generated `__init__.py`; see [collections](collections.md#package-discovery-flat-or-nested).

The generated package's environment is not the persistent uv tool environment. To use its tasks elsewhere, install/link it in that consumer environment; see [plugins](plugins.md#persistent-uv-tool-lifecycle).

## Custom Copier templates

Template source priority for a task collection package is:

1. Explicit `--template` path or Git URL.
2. Git configuration `invoke-toolkit.package-template`.
3. The bundled `package-template` directory.

Origin: [#48](https://github.com/D3f0/invoke-toolkit/pull/48).

The explicit path/URL is passed to Copier. A custom template must accept the template data used by Toolkit: `package_name`, `package_slug`, `python_version`, `collection_name` and `extension_short_name`; any additional answers need usable Copier defaults. See [Copier template authoring](https://copier.readthedocs.io/en/stable/creating/) before replacing the bundled template.

For a concrete local template test in a repository checkout, use its actual bundled template as an explicit source:

```bash
package_parent=$(mktemp -d)
intk -x create.package --ext-name explicit-demo --location "$package_parent" --template "$PWD/templates/package-template"
```

Run that command from the Invoke Toolkit checkout after installing the Copier extra; `$PWD/templates/package-template` is a repository path, not a path promised in an arbitrary installed package. Git config can point to a real trusted template path/URL at repository, user or system scope; it is read with ordinary `git config --get`, so normal Git config precedence applies.

Generation calls Copier with defaults, overwrite enabled, `unsafe=True` and template tasks skipped. The Git-directory/target-existence guard reduces accidental edits but is **not a sandbox or supply-chain boundary**. Use only trusted templates; remote templates and template extensions can introduce code and dependencies you need to review. The guard can be bypassed if Git is absent or its check times out, so choose a safe target yourself.

Copier is imported only when creation needs it; ordinary listing/completion does not eagerly load it ([#144](https://github.com/D3f0/invoke-toolkit/pull/144)).

## Resolver-only packages

`--provider` creates a package that exposes only an `invoke_toolkit.field_resolver` entry point. It never creates a collection entry point or `intk` tasks and ignores the generic task-template Git override. It cannot be combined with `--name`, `--ext-name` or `--template`. Schemes are lowercased and must match `[a-z][a-z0-9-]*`.

The following generates `invoke-toolkit-env-provider` in another fresh parent:

```bash
provider_parent=$(mktemp -d)
intk -x create.package --provider env --location "$provider_parent"
```

**The generated resolver is intentionally unimplemented. Replace it before running its tests or consuming it.** Save this complete implementation as `src/invoke_toolkit_env_provider/__init__.py` inside the generated package:

```python
"""Resolve env://VARIABLE references from the consumer environment."""

import os
from collections.abc import Mapping, Sequence

from invoke_toolkit import Context, FieldResolutionRequest


def resolve(
    ctx: Context,
    requests: Sequence[FieldResolutionRequest],
) -> Mapping[str, str]:
    values = {}
    for request in requests:
        scheme, variable = request.reference.split("://", 1)
        if scheme != "env" or not variable.isidentifier():
            raise ValueError("Expected an env://VARIABLE reference")
        values[request.parameter] = os.environ[variable]
    return values


__all__ = ["resolve"]
```

This implementation resolves real environment values; it is not a mock secret-manager backend. The generated metadata contains:

```toml
[project.entry-points."invoke_toolkit.field_resolver"]
env = "invoke_toolkit_env_provider:resolve"
```

The generated test also expects an unimplemented resolver. Replace `tests/test_resolver.py` inside the generated package with this complete test before running the generated project's test command:

```python
from invoke_toolkit import Context, FieldResolutionRequest
from invoke_toolkit_env_provider import resolve


def test_resolve_environment_batch(monkeypatch) -> None:
    monkeypatch.setenv("DOCS_MESSAGE", "Documentation example")
    requests = [FieldResolutionRequest("message", "env://DOCS_MESSAGE", str)]
    assert resolve(Context(), requests) == {"message": "Documentation example"}
```

```bash
uv sync --directory "$provider_parent/invoke-toolkit-env-provider"
uv run --directory "$provider_parent/invoke-toolkit-env-provider" pytest
```

Install it into the same environment as the consumer. For an isolated POSIX example:

```bash
uv venv "$provider_parent/consumer-env"
uv pip install --python "$provider_parent/consumer-env/bin/python" -e "$provider_parent/invoke-toolkit-env-provider"
```

Save this complete consumer as `$provider_parent/consumer.py`:

```python
from invoke_toolkit import Context, Field, script, task


@task
def show(ctx: Context, message: str = Field(default="env://DOCS_MESSAGE")) -> None:
    """Show the length, not a potentially sensitive value."""
    print(len(message))


if __name__ == "__main__":
    script()
```

```bash
DOCS_MESSAGE='Documentation example' "$provider_parent/consumer-env/bin/python" "$provider_parent/consumer.py" show
```

Global provider use emits a warning recommending a task-local resolver. Consumers can instead import `resolve` and bind `Field(resolver=resolve)` to make that dependency explicit. The [Fields guide](fields.md#task-local-batched-uri-resolvers) specifies batching, exact string result keys and managed Path lifetimes. Providers return text; they do not create temporary paths themselves.

Provider-only packages are outside the `plugin.*` collection lifecycle's collection-entry-point ownership rules. Install them with the consumer's package/environment manager, not by assuming `plugin.list` or `plugin.update` manages them.

Origin: [#128](https://github.com/D3f0/invoke-toolkit/pull/128).
