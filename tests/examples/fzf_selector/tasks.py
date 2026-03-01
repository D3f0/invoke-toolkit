"""
Example tasks demonstrating fzf selector utilities.

This example shows how to use the fzf integration for interactive selection
in tasks. Requires fzf to be installed: https://github.com/junegunn/fzf

Try these commands:
    intk deploy              # Select deployment target interactively
    intk checkout            # Select git branch with preview
    intk test-select         # Select test files to run
    intk docker-logs         # Select docker container and view logs
    intk cleanup             # Select files to delete
"""

from typing import Annotated

from invoke_toolkit import Context, task
from invoke_toolkit.utils.fzf import select, select_from_command


@task
def deploy(ctx: Context):
    """
    Deploy to a target environment with interactive selection.

    Uses fzf to select from predefined deployment targets.
    Falls back to rich-based selection if fzf is not installed.
    """
    # Define available targets
    targets = [
        "production-us-east",
        "production-us-west",
        "production-eu-west",
        "staging-us-east",
        "staging-eu-west",
        "development-local",
    ]

    # Interactive selection
    target = select(ctx, targets, prompt="Select deployment target", height="50%")

    if target:
        print(f"Deploying to {target}...")
        # ctx.run(f"./deploy.sh {target}")
        print(f"✓ Deployed to {target}")
    else:
        print("Deployment cancelled")


@task
def checkout(ctx: Context):
    """
    Checkout a git branch with interactive selection and preview.

    Uses fzf to select from git branches with a preview showing recent commits.
    Falls back to rich-based selection if fzf is not installed.
    """
    # Select from git branches with preview
    branch = select_from_command(
        ctx,
        "git branch --all | sed 's/^[* ]*//'",
        prompt="Select branch",
        preview="git log --oneline --graph --color=always {}",
        preview_window="right:60%",
        ansi=True,  # Enable ANSI color codes
    )

    if branch:
        branch = branch.strip()
        print(f"Checking out {branch}...")
        ctx.run(f"git checkout {branch}")
    else:
        print("Checkout cancelled")


@task
def test_select(ctx: Context):
    """
    Select test files to run interactively.

    Uses fzf to select multiple test files with preview of file contents.
    Falls back to rich-based selection if fzf is not installed.
    """
    # Select test files with multi-select
    selected = select_from_command(
        ctx,
        "find tests/ -name 'test_*.py' -type f",
        prompt="Select test files (Tab for multi-select)",
        multi=True,
        preview="head -50 {}",
        preview_window="right:50%",
        height="60%",
    )

    if selected:
        test_files = " ".join(selected)
        print(f"Running tests: {test_files}")
        ctx.run(f"pytest {test_files} -v")
    else:
        print("No tests selected")


@task
def docker_logs(ctx: Context):
    """
    View logs for a docker container with interactive selection.

    Uses fzf to select from running containers with log preview.
    Falls back to rich-based selection if fzf is not installed.
    """
    # Check if docker is available
    result = ctx.run("docker ps --format '{{.Names}}'", warn=True, hide=True)
    if not result.ok:
        ctx.rich_exit("Docker is not running or not installed")

    # Select container with log preview
    container = select_from_command(
        ctx,
        "docker ps --format '{{.Names}}'",
        prompt="Select container",
        preview="docker logs --tail 50 {}",
        preview_window="down:60%",
        height="40%",
    )

    if container:
        print(f"Following logs for {container}...")
        ctx.run(f"docker logs -f {container}")
    else:
        print("Log viewing cancelled")


@task
def cleanup(
    ctx: Context,
    pattern: Annotated[str, "File pattern to search for"] = "*.pyc",
):
    """
    Interactively select files to delete.

    Uses fzf to select files matching a pattern for deletion.
    Multi-select is enabled for deleting multiple files at once.
    Falls back to rich-based selection if fzf is not installed.
    """
    # Find files and select for deletion
    files = select_from_command(
        ctx,
        f"find . -name '{pattern}' -type f",
        prompt="Select files to delete (Tab for multi-select, Ctrl-C to cancel)",
        multi=True,
        preview="ls -lh {} && echo '---' && head -20 {}",
        preview_window="right:50%",
    )

    if files:
        print(f"Deleting {len(files)} file(s)...")
        for f in files:
            print(f"  Removing: {f}")
            ctx.run(f"rm {f}")
        print("✓ Cleanup complete")
    else:
        print("No files selected for deletion")


@task
def select_config(ctx: Context):
    """
    Select configuration environment with custom styling.

    Demonstrates using custom fzf options for styling.
    Falls back to rich-based selection if fzf is not installed.
    """
    configs = [
        "development.yaml",
        "staging.yaml",
        "production.yaml",
        "test.yaml",
    ]

    # Select with custom styling
    config = select(
        ctx,
        configs,
        prompt="Select config file",
        preview="cat configs/{}",
        border="rounded",
        header="Available configurations",
        height="60%",
        reverse=True,
    )

    if config:
        print(f"Using configuration: {config}")
        # ctx.run(f"export CONFIG_FILE=configs/{config}")
    else:
        print("No configuration selected")


@task
def aws_profile(ctx: Context):
    """
    Select AWS profile interactively.

    Reads AWS profiles from ~/.aws/config and allows selection.
    Falls back to rich-based selection if fzf is not installed.
    """
    # Select AWS profile
    profile = select_from_command(
        ctx,
        "aws configure list-profiles 2>/dev/null || grep '\\[profile' ~/.aws/config | sed 's/\\[profile \\(.*\\)\\]/\\1/'",
        prompt="Select AWS profile",
        preview="aws configure list --profile {}",
        height="40%",
    )

    if profile:
        print(f"Setting AWS profile to: {profile}")
        print(f"Run: export AWS_PROFILE={profile}")
    else:
        print("No profile selected")


@task
def kill_process(ctx: Context):
    """
    Interactively select and kill a process.

    Uses fzf to select from running processes with details preview.
    WARNING: This will actually kill the selected process!
    Falls back to rich-based selection if fzf is not installed.
    """
    # Select process to kill
    process = select_from_command(
        ctx,
        "ps aux | tail -n +2",
        prompt="Select process to kill (Ctrl-C to cancel)",
        preview="echo {} | awk '{print $2}' | xargs ps -p",
        preview_window="down:40%",
        height="60%",
    )

    if process:
        pid = process.split()[1]
        print(f"Killing process {pid}...")
        result = ctx.run(f"kill {pid}", warn=True)
        if result.ok:
            print(f"✓ Process {pid} killed")
        else:
            print(f"✗ Failed to kill process {pid}")
    else:
        print("No process selected")
