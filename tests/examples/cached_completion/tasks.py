"""
Example demonstrating @cached decorator for completion callbacks.

This example shows how to use the @cached decorator for persistent disk-based
caching of completion callbacks. This is essential for shell completion, where
each completion request happens in a separate process.

The @cached decorator uses diskcache to store results on disk, so they persist
across separate shell completion invocations. Requires: pip install diskcache

Try these commands:
    intk deploy --help  # Tab complete after --target to see cached results
    intk checkout --help  # Tab complete after --branch to see git branches

Note: First completion will be slow, subsequent ones will be instant due to caching.
"""

import time
from typing import Annotated

from invoke_toolkit import Context, cached, task


@cached(ttl=300)  # Cache for 5 minutes
def complete_deployment_targets(ctx: Context, incomplete: str) -> list[str]:
    """
    Completion callback with persistent disk-based caching.

    This simulates an expensive API call that fetches deployment targets.
    The @cached decorator uses diskcache to store results on disk, so they
    persist across separate shell completion processes. The TTL of 300 seconds
    (5 minutes) ensures data stays reasonably fresh.

    First completion: ~2 seconds (simulated API call)
    Subsequent completions: <50ms (from disk cache)
    """
    print("Fetching deployment targets... (this is slow)")
    # Simulate expensive API call
    time.sleep(2)

    # Simulated API response
    targets = [
        "production-us-east",
        "production-us-west",
        "production-eu-west",
        "staging-us-east",
        "staging-eu-west",
        "dev-local",
    ]

    # Filter by incomplete prefix
    if incomplete:
        targets = [t for t in targets if t.startswith(incomplete)]

    return sorted(targets)


@cached(ttl=60)  # Cache for 1 minute
def complete_git_branches(ctx: Context, incomplete: str) -> list[str]:
    """
    Completion callback with cached git branch listing.

    Fetches git branches and caches the result to disk. The short TTL (60 seconds)
    ensures the branch list stays fresh, while still providing significant speedup
    for rapid tab-completions within a minute.

    The @cached decorator persists results across processes, so all shell
    completion requests benefit from the cache.
    """
    # Run git command to get branches
    result = ctx.run("git branch --list", hide=True, warn=True)

    if result.ok:
        branches = [
            line.strip().lstrip("* ")
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        # Filter by incomplete prefix
        if incomplete:
            branches = [b for b in branches if b.startswith(incomplete)]

        return sorted(branches)

    return []


@task
def deploy(
    ctx: Context,
    target: Annotated[str, complete_deployment_targets],
    version: str = "latest",
) -> None:
    """
    Deploy to a target environment with persistent cached completion.

    The first time you tab-complete the --target option, it will be slow (~2s).
    Subsequent tab-completions will be instant (<50ms) because results are
    cached to disk. The cache persists across shell sessions and is valid for
    5 minutes (as specified in the @cached decorator).

    Args:
        target: Deployment target (with persistent cached completion)
        version: Version to deploy (default: latest)
    """
    print(f"Deploying version {version} to {target}...")
    # Deployment logic here
    print(f"✓ Successfully deployed to {target}")


@task
def checkout(
    ctx: Context,
    branch: Annotated[str, complete_git_branches],
) -> None:
    """
    Checkout a git branch with persistent cached completion.

    Tab-complete the --branch option to see available branches.
    Branch listing is cached to disk for 1 minute, providing fast
    completions across multiple shell completion requests.

    Args:
        branch: Git branch name (with persistent cached completion)
    """
    ctx.run(f"git checkout {branch}")
    print(f"✓ Checked out branch: {branch}")


# Example: Different TTL values for different data types


@cached(ttl=30)  # Short TTL for frequently changing data
def complete_active_deployments(ctx: Context, incomplete: str) -> list[str]:
    """
    Completion for active deployments (changes frequently).

    Short TTL (30 seconds) ensures data stays fresh while still providing
    speedup for rapid completions.
    """
    print("Fetching active deployments...")
    time.sleep(1)
    # Simulated API call
    deployments = ["deploy-abc123", "deploy-def456", "deploy-ghi789"]

    if incomplete:
        deployments = [d for d in deployments if d.startswith(incomplete)]

    return sorted(deployments)


@cached(ttl=3600)  # Long TTL for stable data
def complete_databases(ctx: Context, incomplete: str) -> list[str]:
    """
    Completion for database names (rarely changes).

    Long TTL (1 hour) because database names are stable and don't change often.
    """
    print("Fetching database names from API...")
    time.sleep(1)
    databases = ["users_db", "products_db", "analytics_db", "logs_db"]

    if incomplete:
        databases = [d for d in databases if d.startswith(incomplete)]

    return sorted(databases)


@task
def backup(
    ctx: Context,
    database: Annotated[str, complete_databases],
    output_dir: str = "./backups",
) -> None:
    """
    Backup a database with persistent cached completion.

    Database names are cached for 1 hour since they rarely change.
    The persistent disk cache means fast completions across all shell sessions.

    Args:
        database: Database name (with persistent cached completion)
        output_dir: Output directory for backups
    """
    print(f"Backing up {database} to {output_dir}...")
    # Backup logic here
    print(f"✓ Backup completed: {database}")
