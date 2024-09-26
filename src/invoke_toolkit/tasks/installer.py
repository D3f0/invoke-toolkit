from invoke import task, Context
from invoke_toolkit.github import get_latest_release
from invoke_toolkit.output import console, rich_exit

# This should be added to the collection
config = {}


@task()
def latest_release(ctx: Context, repo="microsoft/vscode"):
    output = get_latest_release(ctx, repo=repo)
    console.print(output)


@task()
def install(ctx: Context, program=[]): ...


@task()
def web_installer(ctx: Context, binary_name: str = ""):
    if not binary_name:
        rich_exit("Please provide a binary name")
