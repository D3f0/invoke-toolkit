"""
Example demonstrating completion callbacks that read from config files.

This example shows how completion callbacks can use ctx.get_config_value()
to read values from invoke.yaml (or other config sources) and provide
dynamic completions based on project configuration.

The invoke.yaml file in this directory contains:
- deployment.environments: List of deployment environments
- deployment.regions: List of available regions
- database.instances: List of database instances
- database.profiles: List of connection profiles
- features.available_flags: List of feature flags

Try these commands (from this directory):
    cd tests/examples/completion_config
    intk deploy --environment <TAB>    # Shows environments from config
    intk deploy --region <TAB>         # Shows regions from config
    intk connect-db --instance <TAB>   # Shows database instances from config
    intk toggle-feature --flag <TAB>   # Shows feature flags from config

Key benefits:
- Completions are driven by configuration, not hardcoded
- Users can customize available options via config files
- Same config values can be used by both tasks and completions
- Supports user (~/.invoke.yaml), system (/etc/invoke.yaml), and project config
"""

from typing import Annotated

from invoke_toolkit import Context, task


def complete_environments(ctx: Context, incomplete: str) -> list[str]:
    """
    Completion callback that reads deployment environments from config.

    The context (`ctx`) passed to this callback is now pre-loaded with
    the project's configuration, so we can directly query values.
    """
    environments = ctx.get_config_value(
        "deployment.environments",
        default=["development", "staging", "production"],
    )

    # Filter by incomplete prefix
    if incomplete:
        environments = [e for e in environments if e.startswith(incomplete)]

    return sorted(environments)


def complete_regions(ctx: Context, incomplete: str) -> list[str]:
    """Completion callback that reads available regions from config."""
    regions = ctx.get_config_value(
        "deployment.regions",
        default=["us-east-1", "us-west-2", "eu-west-1"],
    )

    if incomplete:
        regions = [r for r in regions if r.startswith(incomplete)]

    return sorted(regions)


def complete_db_instances(ctx: Context, incomplete: str) -> list[str]:
    """Completion callback for database instances."""
    instances = ctx.get_config_value(
        "database.instances",
        default=["primary-db", "replica-db"],
    )

    if incomplete:
        instances = [i for i in instances if i.startswith(incomplete)]

    return sorted(instances)


def complete_db_profiles(ctx: Context, incomplete: str) -> list[str]:
    """Completion callback for database connection profiles."""
    profiles = ctx.get_config_value(
        "database.profiles",
        default=["readonly", "readwrite"],
    )

    if incomplete:
        profiles = [p for p in profiles if p.startswith(incomplete)]

    return sorted(profiles)


def complete_feature_flags(ctx: Context, incomplete: str) -> list[str]:
    """Completion callback for feature flags."""
    flags = ctx.get_config_value(
        "features.available_flags",
        default=["debug_mode", "beta_features"],
    )

    if incomplete:
        flags = [f for f in flags if f.startswith(incomplete)]

    return sorted(flags)


@task
def deploy(
    ctx: Context,
    environment: Annotated[str, complete_environments],
    region: Annotated[str, complete_regions] = "",
) -> None:
    """
    Deploy the application to a specified environment.

    The --environment and --region arguments have tab completion that reads
    available options from invoke.yaml configuration.

    Examples:
        intk deploy --environment staging
        intk deploy --environment production --region eu-west-1
    """
    # Read the default region from config if not specified
    if not region:
        region = ctx.get_config_value("deployment.default_region", default="us-east-1")

    ctx.print(f"[green]Deploying to {environment} in {region}[/green]")

    # In a real task, you would do the actual deployment here
    ctx.print(f"  Environment: {environment}")
    ctx.print(f"  Region: {region}")


@task
def connect_db(
    ctx: Context,
    instance: Annotated[str, complete_db_instances],
    profile: Annotated[str, complete_db_profiles] = "readonly",
) -> None:
    """
    Connect to a database instance.

    Both --instance and --profile have completions from config.

    Examples:
        intk connect-db --instance primary-db
        intk connect-db --instance analytics-db --profile admin
    """
    ctx.print("[cyan]Connecting to database[/cyan]")
    ctx.print(f"  Instance: {instance}")
    ctx.print(f"  Profile: {profile}")


@task
def toggle_feature(
    ctx: Context,
    flag: Annotated[str, complete_feature_flags],
    enable: bool = True,
) -> None:
    """
    Toggle a feature flag.

    The --flag argument completes with available feature flags from config.

    Examples:
        intk toggle-feature --flag dark_mode
        intk toggle-feature --flag beta_features --no-enable
    """
    action = "Enabling" if enable else "Disabling"
    ctx.print(f"[yellow]{action} feature flag: {flag}[/yellow]")


@task
def show_config(ctx: Context) -> None:
    """
    Display the current configuration values used for completions.

    This task shows what values the completion callbacks will use,
    which helps verify your configuration is loaded correctly.
    """
    ctx.print("[bold]Current completion configuration:[/bold]\n")

    # Show completion timeout
    timeout = ctx.get_config_value("completion.callback_timeout", default=10.0)
    ctx.print(f"[cyan]Completion timeout:[/cyan] {timeout}s\n")

    # Show deployment config
    ctx.print("[cyan]Deployment environments:[/cyan]")
    environments = ctx.get_config_value("deployment.environments", default=[])
    for env in environments:
        ctx.print(f"  - {env}")

    ctx.print(
        f"\n[cyan]Default region:[/cyan] {ctx.get_config_value('deployment.default_region', default='not set')}"
    )

    ctx.print("\n[cyan]Available regions:[/cyan]")
    regions = ctx.get_config_value("deployment.regions", default=[])
    for region in regions:
        ctx.print(f"  - {region}")

    # Show database config
    ctx.print("\n[cyan]Database instances:[/cyan]")
    instances = ctx.get_g_config_value("database.instances", default=[])
    for instance in instances:
        ctx.print(f"  - {instance}")

    ctx.print("\n[cyan]Database profiles:[/cyan]")
    profiles = ctx.get_config_value("database.profiles", default=[])
    for profile in profiles:
        ctx.print(f"  - {profile}")

    # Show feature flags
    ctx.print("\n[cyan]Feature flags:[/cyan]")
    flags = ctx.get_config_value("features.available_flags", default=[])
    for flag in flags:
        ctx.print(f"  - {flag}")
