# Completion Config Example

This example demonstrates how completion callbacks can read values from configuration files using `ctx.get_config_value()`.

## Overview

Instead of hardcoding completion options, this example shows how to:
- Read completion values from `invoke.yaml` configuration
- Use `ctx.get_config_value()` method (no import needed)
- Provide fallback defaults when config is missing
- Share config values between tasks and completion callbacks

## Files

- `invoke.yaml` - Configuration file with completion values
- `tasks.py` - Tasks with completion callbacks that read from config

## Usage

```bash
# Navigate to this directory
cd tests/examples/completion_config

# View current config values
intk show-config

# Try tab completion (reads from invoke.yaml)
intk deploy --environment <TAB>
intk deploy --region <TAB>
intk connect-db --instance <TAB>
intk toggle-feature --flag <TAB>
```

## How It Works

### 1. Define completion callback that reads config

```python
def complete_environments(ctx: Context, incomplete: str) -> list[str]:
    # Read from config - no import needed!
    environments = ctx.get_config_value(
        "deployment.environments",
        default=["development", "staging", "production"],
    )
    
    if incomplete:
        environments = [e for e in environments if e.startswith(incomplete)]
    
    return sorted(environments)
```

### 2. Use the callback with Annotated type hint

```python
@task
def deploy(
    ctx: Context,
    environment: Annotated[str, complete_environments],
) -> None:
    ...
```

### 3. Configure values in invoke.yaml

```yaml
deployment:
  environments:
    - development
    - staging
    - production
    - canary
```

## Config Sources

The `ctx.get_config_value()` method reads from the full config hierarchy:

1. **Project config** - `./invoke.yaml` in current directory
2. **User config** - `~/.invoke.yaml` in home directory  
3. **System config** - `/etc/invoke.yaml`
4. **Environment variables** - `INVOKE_*` prefix
5. **Defaults** - Built-in toolkit defaults

## Benefits

- **Dynamic completions** - Options come from config, not code
- **User customizable** - Users can add/remove options via config
- **Shared values** - Same config used by tasks and completions
- **Fallback defaults** - Works even without config file
