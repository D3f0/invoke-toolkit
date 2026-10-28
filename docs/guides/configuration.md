# Configuration and schemas

Toolkit keeps [Invoke's layered configuration](https://docs.pyinvoke.org/en/latest/concepts/configuration.html) and adds dot-path helpers, editing tasks and attrs/cattrs schema access. Configuration is not the same as [Field defaults](fields.md): a schema structures configuration data; a Field defers a task parameter's default until execution.

## Read merged configuration

Save this as `tasks.py` after [installation](../getting-started/installation.md):

```python
from invoke_toolkit import Collection, Context, task


@task
def settings(ctx: Context) -> None:
    """Read application settings without changing files."""
    host = ctx.get_config_value("app.host", default="localhost")
    retries = ctx.get_config_value("app.retries", default=3)
    print(f"host={host}, retries={retries}")


ns = Collection(settings)
ns.configure({"app": {"host": "localhost", "retries": 3}})
```

```bash
intk settings
intk -x config.get app --format json
```

`ctx.get_config_value(path, default=..., exit_message=None, exit_code=None, required=False)` returns existing falsy values—including `None`—unchanged. Missing optional paths return the default, or `None` if no default was supplied. `required=True`, `exit_message` or `exit_code` requests a Rich exit when the path is missing; a supplied default does not override that requirement. The same helper is available as `invoke_toolkit.config.get_config_value(ctx, ...)`.

Invoke merges defaults, collection values, system/user/project files, environment settings, runtime configuration and explicit overrides according to its hierarchy. Ordinary `tasks.py` loading sets the project location to the discovered task collection's directory. [PEP 723 `script()`](../pep723/index.md) loads project configuration from the current working directory.

Origins: helper and script prefix [#11](https://github.com/D3f0/invoke-toolkit/pull/11), context method [#94](https://github.com/D3f0/invoke-toolkit/pull/94), script project loading [#104](https://github.com/D3f0/invoke-toolkit/pull/104).

## Inspect and edit configuration files

The built-in collection requires `-x`. Reading returns the **merged** configuration; setting and unsetting edit one selected file, not every layer.

```bash
intk -x config.get run.echo
intk -x config.get app --format yaml
intk -x config.show --format json
intk -x config.set --path custom_ports --value '[8080, 8443]' --location local --format json
intk -x config.get custom_ports --format json
intk -x config.unset --path custom_ports --location local
```

Run editing examples in a scratch project: they persist changes. `--format` selects `config.get` output (`raw`, `json`, `yaml`, `python`), or the new file format for `config.set` (`yaml` or `json`). An existing file keeps its format. `config.show` exports serializable sections by default and writes a diagnostic to stderr; do not treat every built-in command as universal JSON. `config.get` reports missing paths on stderr and returns no value rather than guaranteeing failure status.

Use explicit `--path` and `--value` with current Toolkit. Historical positional `config.set PATH VALUE` documentation came from [#71](https://github.com/D3f0/invoke-toolkit/pull/71); current signatures have optional path/value defaults and no positional decorator override. The complete CLI reference is [here](../reference/cli.md).

### Formats and locations

| `--location` | Default filename | Existing file candidates |
| --- | --- | --- |
| `local` (default) | `./invoke.yaml` | `./invoke.yaml`, `./invoke.yml`, `./invoke.json`, `./invoke.py` |
| `user` | `~/.invoke.yaml` | Same suffixes under `~/.invoke` |
| `system` | `/etc/invoke.yaml` | Same suffixes under `/etc/invoke` |

The first existing candidate is edited. `--format json` only chooses JSON when there is no existing candidate; an unrecognized new-file format falls back to YAML. Custom config classes' prefixes change these names. `local` writes relative to **the current directory**, which need not be the discovered task file's project directory. `--location` is an editing-task option, not a global switch for reading just one layer. System writes require appropriate filesystem permissions; no sudo is performed for you.

Values are parsed by `ast.literal_eval`, then retained as strings if parsing fails. Use Python literals: `True`, `False`, `None`, numbers, quoted strings, lists and dictionaries. Shell quotes protect the whole literal: `--value "{'debug': True}"`. JSON `true` is not a Python boolean literal. These files are settings, not secret stores; values on the CLI can appear in history and process arguments.

YAML/YML/JSON files are rewritten as serialized data, so comments/formatting are not preserved. Existing Python config files are executed while loading and rewritten as simple serializable assignments while editing; arbitrary Python code and nonserializable values are not preserved. Prefer YAML/JSON and inspect a backup/diff when editing important files.

Origins: [#52](https://github.com/D3f0/invoke-toolkit/pull/52), existing-value validation repairs [#65](https://github.com/D3f0/invoke-toolkit/pull/65), unset [#93](https://github.com/D3f0/invoke-toolkit/pull/93).

### Validation and unset limits

`config.set` checks a registered schema's field type first, then the existing merged value's basic type. It allows an integer for a float and skips existing-value checks for unknown paths or values currently `None`. New paths without a registered schema are not universally validated. `--no-validate` skips **schema validation only**; existing-value validation still applies. Some existing-value errors print diagnostics and return without a nonzero exit, so automation should inspect persisted data rather than assuming exit status proves a write.

Unsetting a file value may reveal a lower-priority default instead of making the merged path disappear. `config.unset` prunes empty parent dictionaries. There is a current nested-edit limitation: if deletion mutates a shared nested dictionary and leaves its parent nonempty, its shallow change comparison can report no change and skip saving. The top-level `custom_ports` example avoids this case. Check the selected file after nested unsets; manually edit that file if the value remains.

## attrs and cattrs schemas

Define a `ConfigSchema` subclass with `@config_schema` (which applies attrs and registers the schema) or `@attrs.define`. Include `ConfigSchema` inheritance when using `Config.as_schema()` or `Collection.configure(schema=...)`; a decorator-only class gets helper methods but does not become a `ConfigSchema` subclass.

This complete `tasks.py` uses nested schemas, explicit root placement and an editable configuration view:

```python
import attrs

from invoke_toolkit import Collection, Context, task
from invoke_toolkit.config import ConfigSchema, config_schema


@attrs.define
class DatabaseConfig(ConfigSchema):
    host: str = "localhost"
    port: int = 5432


@config_schema("app", description="Application settings")
class AppConfig(ConfigSchema):
    debug: bool = False
    database: DatabaseConfig = attrs.Factory(DatabaseConfig)


@task
def show_settings(ctx: Context) -> None:
    """Read a typed snapshot and update only in-memory configuration."""
    app = ctx.get_schema(AppConfig)
    print(f"database={app.database.host}:{app.database.port}, debug={app.debug}")
    app.debug = True
    ctx.config.update_from(app, "app")
    print(f"in-memory debug={ctx.get_schema(AppConfig).debug}")


ns = Collection(show_settings)
ns.configure({"app": AppConfig().to_dict()})
```

```bash
intk show-settings
intk -x config.schemas --collection app --verbose
intk -x config.set --path app.database.port --value 3306
intk show-settings
```

The schema is imported and registered with `tasks.py`, so the built-in editing task sees it. `ConfigSchema.from_dict(data)` and `.to_dict()` use cattrs; structuring follows its conversion rules and can raise `cattrs.ClassValidationError`. Register custom conversion hooks with `ConfigSchema.get_converter()` when needed. This is distinct from the CLI editor's basic field-type validation, not automatic validation of every config layer on load.

- `config.as_schema(AppConfig, "app")` requires that path to exist and raises `KeyError` otherwise.
- `ctx.get_schema(AppConfig)` uses the decorator's collection path; it returns schema defaults if the path is absent. Without registered path metadata, provide a path explicitly.
- Schema objects are snapshots. Mutating one does not affect config until `config.update_from(schema, path)`; that updates in-memory configuration, **not** a config file.
- `collection.configure(schema=SchemaClass)` applies class defaults; a schema instance applies its values. `mapping` is deep-merged over those values. This places fields directly in that collection's configuration; a collection name does not automatically wrap them in a root dictionary. Choose your task's access path explicitly, as in the example.
- `Collection.from_package()` discovers module `config_schema` attributes; registration alone is not installation of defaults. See [collections](collections.md#module-configuration-with-from_package).

Origin: [#90](https://github.com/D3f0/invoke-toolkit/pull/90).

## Custom configuration classes

Toolkit `Config` accepts subclass options `prefix`, `file_prefix`, `env_prefix` and `extra_defaults`. `extra_defaults` deep-merges with upstream defaults before Toolkit's runner/completion/fzf settings are installed. For an embedded application, import the actual Toolkit program class:

```python
from invoke_toolkit import Collection, Config, Context, task
from invoke_toolkit.program import ToolkitProgram


class AppConfig(Config, prefix="myapp", extra_defaults={"app": {"retries": 4}}):
    """Load myapp-named configuration files."""


@task
def settings(ctx: Context) -> None:
    print(ctx.get_config_value("app.retries"))


if __name__ == "__main__":
    ToolkitProgram(namespace=Collection(settings), config_class=AppConfig).run()
```

Save as `app.py` and run `python app.py settings` in the installed environment. `script(config_prefix="myapp")` is the simpler portable-script alternative; see [PEP 723](../pep723/index.md). The root export `Program` is upstream Invoke's class, **not** an alias for `ToolkitProgram`.
