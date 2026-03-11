"""Weather tasks with typed config schema.

This demonstrates how to define config schemas using the @config_schema decorator.
The schema is registered automatically when the decorator is applied.
"""

from __future__ import annotations

import attrs

from invoke_toolkit import task
from invoke_toolkit.collections import ToolkitCollection
from invoke_toolkit.config import ConfigSchema, config_schema
from invoke_toolkit.context import ToolkitContext


# =============================================================================
# Config Schema Definition
# =============================================================================


@config_schema("weather.api", description="Weather API connection settings")
class WeatherAPIConfig(ConfigSchema):
    """Configuration for the weather API connection."""

    api_key: str = ""
    base_url: str = "https://api.openweathermap.org/data/2.5"
    timeout: float = 30.0
    units: str = "metric"  # metric, imperial, kelvin


@config_schema("weather", description="Weather extension configuration")
class WeatherConfig(ConfigSchema):
    """Root configuration for the weather extension.

    When using collection.configure(schema=...), the config is merged at
    collection scope. Access it without a path prefix in as_schema().

    In invoke.yaml, use the collection name as the namespace:
        weather:
          default_city: "London"
          api:
            api_key: "your-api-key"  # pragma: allowlist secret
            units: "imperial"
    """

    default_city: str = "New York"
    cache_ttl: int = 300  # seconds
    api: WeatherAPIConfig = attrs.Factory(WeatherAPIConfig)


# =============================================================================
# Collection Setup
# =============================================================================

collection = ToolkitCollection("weather")

# Register the config schema - this enables validation for config.set
collection.configure(schema=WeatherConfig)


# =============================================================================
# Tasks
# =============================================================================


@task
def forecast(ctx: ToolkitContext, city: str | None = None, days: int = 3) -> None:
    """Get weather forecast for a city.

    Args:
        city: City name (uses config default if not provided)
        days: Number of days to forecast (1-7)

    Example:
        intk weather.forecast --city "London" --days 5
    """
    # Access typed config (no path prefix - collection config is merged at root)
    config = ctx.config.as_schema(WeatherConfig)

    city = city or config.default_city

    ctx.print(f"[bold]Weather forecast for {city}[/bold]")
    ctx.print(f"API: {config.api.base_url}")
    ctx.print(f"Units: {config.api.units}")
    ctx.print(f"Days: {days}")

    if not config.api.api_key:
        ctx.print("[yellow]Warning: No API key configured[/yellow]")
        ctx.print(
            "Set with: intk config.set --path weather.api.api_key --value '\"your-key\"'"
        )


@task
def current(ctx: ToolkitContext, city: str | None = None) -> None:
    """Get current weather for a city.

    Args:
        city: City name (uses config default if not provided)

    Example:
        intk weather.current
        intk weather.current --city "Tokyo"
    """
    config = ctx.config.as_schema(WeatherConfig)
    city = city or config.default_city

    ctx.print(f"[bold]Current weather in {city}[/bold]")
    ctx.print("(Demo mode - no actual API call)")


@task
def config_info(ctx: ToolkitContext) -> None:
    """Show current weather configuration.

    Example:
        intk weather.config-info
    """
    config = ctx.config.as_schema(WeatherConfig)

    ctx.print("[bold]Weather Extension Configuration[/bold]")
    ctx.print(f"  Default city: {config.default_city}")
    ctx.print(f"  Cache TTL: {config.cache_ttl}s")
    ctx.print(f"  API URL: {config.api.base_url}")
    ctx.print(f"  API Key: {'***' if config.api.api_key else '[red]Not set[/red]'}")
    ctx.print(f"  Units: {config.api.units}")
    ctx.print(f"  Timeout: {config.api.timeout}s")


# Add tasks to collection
collection.add_task(forecast)  # type: ignore[arg-type]
collection.add_task(current)  # type: ignore[arg-type]
collection.add_task(config_info, name="config-info")  # type: ignore[arg-type]
