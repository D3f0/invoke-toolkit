from invoke import Context, task


@task(default=True)
def install(ctx: Context):
    """
    Installation of Python completions.
    This is a re-implementation of inv[oke] --print-completion-script
    """
