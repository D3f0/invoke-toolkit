# invoke-toolkit-weather

Example extension demonstrating config schemas for invoke-toolkit.

## Installation

```bash
# From the examples directory
pip install -e examples/invoke-toolkit-weather
```

## Usage

```bash
# List available tasks
intk --list

# Get weather forecast
intk weather.forecast --city "London"

# Show configuration
intk weather.config-info

# Set configuration (with validation!)
intk config.set --path weather.default_city --value '"Paris"'
intk config.set --path weather.api.api_key --value '"your-api-key"'
intk config.set --path weather.api.units --value '"imperial"'

# This will fail validation (cache_ttl expects int):
# intk config.set --path weather.cache_ttl --value '"not-a-number"'
```

## Config Schema

The extension defines a typed config schema in `tasks.py`:

```python
@attrs.define
class WeatherConfig(ConfigSchema):
    default_city: str = "New York"
    cache_ttl: int = 300
    api: WeatherAPIConfig = attrs.Factory(WeatherAPIConfig)

# Register with the collection
collection.configure(schema=WeatherConfig)
```

In task code, access the config without a path prefix (the collection config
is merged at the collection scope):

```python
@task
def my_task(ctx: ToolkitContext) -> None:
    config = ctx.config.as_schema(WeatherConfig)  # No path prefix needed
    print(config.default_city)
```

This enables:
- IDE autocomplete when accessing config
- Runtime validation in `config.set`
- Self-documenting configuration structure

## invoke.yaml Example

In the YAML config file, use the collection name as the namespace:

```yaml
weather:
  default_city: "London"
  cache_ttl: 600
  api:
    api_key: "your-openweathermap-api-key"  # pragma: allowlist secret
    base_url: "https://api.openweathermap.org/data/2.5"
    units: "metric"
    timeout: 30.0
```
