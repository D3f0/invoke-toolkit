"""Package-root exports are usable without leaking import dependencies."""


def test_wildcard_import_supports_toolkit_task_consumer():
    namespace = {}
    exec(
        "from invoke_toolkit import *\n"
        "@task\n"
        "def greet(ctx: Context, name: str = 'world') -> str:\n"
        '    return f"{ctx.config.greeting}, {name}!"\n'
        "ctx = Context(config=Config(overrides={'greeting': 'Hola'}))\n"
        "collection = Collection(greet)\n"
        "result = collection['greet'](ctx, name='Ada')\n",
        namespace,
    )
    assert namespace["result"] == "Hola, Ada!"
    assert not {"sys", "metadata", "Any"} & namespace.keys()
