"""
Example showing tab completion callbacks that read from ToolkitConfig.

This demonstrates the fix from v0.0.57: completion callbacks now receive a
proper ToolkitContext backed by the program's already-loaded ToolkitConfig,
so they can read project-level invoke.yaml values just like any regular task.

Directory layout::

    completion_with_config/
    ├── tasks.py        # this file
    └── invoke.yaml     # sets deploy.allowed_envs and completion.callback_timeout

Try it::

    # List available tasks
    intk --search-root tests/examples/completion_with_config --list

    # Tab-complete --target: suggestions filtered by deploy.allowed_envs from invoke.yaml
    intk --search-root tests/examples/completion_with_config deploy --target <TAB>

    # Tab-complete --env: only envs listed in deploy.allowed_envs are shown
    intk --search-root tests/examples/completion_with_config deploy --env <TAB>

    # Show which config values are in effect
    intk --search-root tests/examples/completion_with_config show-config

Edit invoke.yaml and change deploy.allowed_envs to see the completions change
without touching this file.
"""

from textwrap import dedent
from typing import Annotated

from invoke_toolkit import Context, task

# ---------------------------------------------------------------------------
# Static data – all known targets, keyed by environment name
# ---------------------------------------------------------------------------

_ALL_TARGETS: dict[str, list[str]] = {
    "dev": ["dev-us-east", "dev-eu-west"],
    "staging": ["staging-us-east", "staging-us-west", "staging-eu-west"],
    "production": ["prod-us-east", "prod-us-west", "prod-eu-west", "prod-ap-south"],
}

# ---------------------------------------------------------------------------
# Completion callbacks
# ---------------------------------------------------------------------------


def complete_environments(ctx: Context, incomplete: str) -> list[str]:
    """Return the environment names permitted by deploy.allowed_envs.

    Reads ``deploy.allowed_envs`` from the project config (invoke.yaml).
    When the key is absent every environment is offered.
    """
    allowed = ctx.get_config_value("deploy.allowed_envs", default=None)

    if allowed:
        envs = [e for e in allowed if e in _ALL_TARGETS]
    else:
        envs = list(_ALL_TARGETS.keys())

    if incomplete:
        envs = [e for e in envs if e.startswith(incomplete)]

    return sorted(envs)


def complete_targets(ctx: Context, incomplete: str) -> list[str]:
    """Return deployment targets restricted to the allowed environments.

    Reads ``deploy.allowed_envs`` from the project config (invoke.yaml) so
    operators can narrow the suggestion list without touching task code.
    """
    allowed = ctx.get_config_value("deploy.allowed_envs", default=None)

    if allowed:
        candidates = [
            t for env in allowed if env in _ALL_TARGETS for t in _ALL_TARGETS[env]
        ]
    else:
        candidates = [t for targets in _ALL_TARGETS.values() for t in targets]

    if incomplete:
        candidates = [t for t in candidates if t.startswith(incomplete)]

    return sorted(candidates)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task
def deploy(
    ctx: Context,
    target: Annotated[str, complete_targets] = "",
    env: Annotated[str, complete_environments] = "dev",
) -> None:
    """Deploy to a target host.

    Tab-complete ``--target`` to see hosts filtered by the environments listed
    in ``deploy.allowed_envs`` (invoke.yaml).
    Tab-complete ``--env`` to see the allowed environment names.

    Args:
        target: Deployment host (tab-complete to see available targets).
        env: Environment name (tab-complete to see choices).
    """
    if not target:
        ctx.rich_exit(
            dedent(
                """\
                [red]No target specified.[/red]
                Run with tab-completion or pass [cyan]--target <host>[/cyan].
                """
            )
        )

    ctx.print(f"[bold]Deploying[/bold] to [cyan]{target}[/cyan] (env: {env})")
    ctx.run(f"echo 'deploy → {target}'")


@task
def show_config(ctx: Context) -> None:
    """Show the config values that drive tab-completion in this example.

    Run this to verify that your invoke.yaml overrides are being picked up.
    """
    timeout = ctx.get_config_value("completion.callback_timeout", default=10.0)
    allowed = ctx.get_config_value("deploy.allowed_envs", default=None)

    ctx.print("[bold]completion_with_config – effective settings[/bold]\n")
    ctx.print(
        dedent(
            f"""\
            completion.callback_timeout = [cyan]{timeout}[/cyan]
            deploy.allowed_envs         = [cyan]{allowed or "<all>"}[/cyan]
            """
        )
    )
