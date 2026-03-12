"""Tasks demonstrating config schema support.

This example shows how to:
1. Define a typed config schema with @config_schema decorator
2. Access config with full IDE autocomplete via ctx.get_schema()
3. Use nested config schemas

Run with:
    intk --search-root tests/examples/config_schema show-config
    intk --search-root tests/examples/config_schema config-demo --debug
"""

from __future__ import annotations

import attrs

from invoke_toolkit import Context, task
from invoke_toolkit.config import ConfigSchema, config_schema


# =============================================================================
# Config Schema Definition
# =============================================================================


@config_schema
class DatabaseConfig(ConfigSchema):
    """Database connection configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "mydb"
    pool_size: int = 5


@config_schema
class CacheConfig(ConfigSchema):
    """Cache configuration."""

    enabled: bool = True
    ttl: int = 300
    max_size: int = 1000


@config_schema("app")
class AppConfig(ConfigSchema):
    """Application configuration.

    Access in invoke.yaml:
        app:
          debug: true
          database:
            host: "prod.db.example.com"
    """

    debug: bool = False
    log_level: str = "INFO"
    database: DatabaseConfig = attrs.Factory(DatabaseConfig)
    cache: CacheConfig = attrs.Factory(CacheConfig)


# =============================================================================
# Tasks
# =============================================================================


@task
def show_config(ctx: Context) -> None:
    """Show the current configuration.

    Demonstrates using ctx.get_schema() for type-safe config access.
    The config object is printed directly - Rich renders it nicely.
    """
    config = ctx.get_schema(AppConfig)
    ctx.print(config)


@task
def config_demo(ctx: Context, debug: bool = False) -> None:
    """Demonstrate config modification with schema.

    Args:
        debug: Override the debug setting
    """
    config = ctx.get_schema(AppConfig)

    ctx.print("[bold cyan]Config Schema Demo[/bold cyan]\n")
    ctx.print(f"Original debug: {config.debug}")
    ctx.print(f"Original log level: {config.log_level}")

    if debug:
        config.debug = True
        config.log_level = "DEBUG"

        ctx.print()
        ctx.print("[yellow]Config modified![/yellow]")
        ctx.print(f"New debug: {config.debug}")
        ctx.print(f"New log level: {config.log_level}")


@task
def validate_demo(ctx: Context) -> None:
    """Demonstrate schema validation.

    Try setting invalid config values to see validation errors.
    """
    ctx.print("[bold]Schema Validation Demo[/bold]\n")
    ctx.print("The @config_schema decorator registers schemas for validation.\n")
    ctx.print("Try these commands:\n")
    ctx.print("  [green]# Valid - port is an integer[/green]")
    ctx.print("  intk config.set --path app.database.port --value 3306\n")
    ctx.print("  [red]# Invalid - port expects int, not string[/red]")
    ctx.print("  intk config.set --path app.database.port --value '\"not-a-number\"'\n")
    ctx.print("  [cyan]# List all schemas[/cyan]")
    ctx.print("  intk config.schemas")
