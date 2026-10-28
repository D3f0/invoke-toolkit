# Task and completion caches

Toolkit has **two different caches**: `@task(cache=...)` stores task return values; `@cached(...)` stores completion callback suggestions. Neither is Invoke's within-invocation task deduplication.

Both require the optional diskcache extra for persistence. Add it to the environment that runs your tasks:

```bash
python -m pip install 'invoke-toolkit[cache]'
```

For a [PEP 723 script](../pep723/index.md), declare `invoke-toolkit[cache]` in its dependency metadata instead. Without diskcache, the task/callback runs normally and caching is disabled; there is no persistent or in-memory fallback promised.

## Authenticated cache storage

Task and completion caches authenticate serialized values with HMAC-SHA256
before deserialization. The owner-only signing key lives under
`platformdirs.user_data_dir("invoke-toolkit")/cache-signing/cache.key`, outside
the cache directory. Unsigned legacy entries and tampered entries are cache
misses and are recomputed. Losing the key invalidates existing entries; if its
permissions or ownership are unsafe, caching is disabled rather than reading
unsigned data.

New entries are stored inline in SQLite. Legacy DiskCache spill files are not
read or deleted automatically, because their filenames are unauthenticated.

Origins: cache authentication [#147](https://github.com/D3f0/invoke-toolkit/pull/147),
backend included in fresh checkouts [#148](https://github.com/D3f0/invoke-toolkit/pull/148).


## Task result cache

Save this complete example as `tasks.py` in the installed environment:

```python
from invoke_toolkit import CacheConfig, Context, cache_stats, clear_task_cache, task


@task(cache=CacheConfig(ttl=60, key_prefix="docs-digest-v1:"), autoprint=True)
def digest(ctx: Context, text: str = "toolkit") -> str:
    """Cache a pure computation, not a side effect."""
    from hashlib import sha256

    return sha256(text.encode("utf-8")).hexdigest()


@task
def show_cache(ctx: Context) -> None:
    """Inspect this repository's task cache."""
    ctx.print(cache_stats())


@task
def clear_docs_cache(ctx: Context) -> None:
    """Remove only the short keys used by this example."""
    print(clear_task_cache("docs-digest-v1:digest"))
```

```bash
intk digest --text toolkit
intk digest --text toolkit
intk show-cache
intk clear-docs-cache
```

The examples deliberately show no invented hit/miss output. `intk --debug digest` enables observed cache diagnostics through debug logging; do not enable debug when secrets may be in memory or configuration.

Accepted `cache` forms:

| Value | Behavior |
| --- | --- |
| `False` or `None` | Disabled (default) |
| `True` | Enabled, no expiration |
| `{"ttl": 60, "key_prefix": "v1:", "ignore_args": ["verbose"]}` | Explicit options |
| `CacheConfig(enabled=True, ttl=None, key_prefix="", ignore_args=[])` | Same options as an object |

Task cache files live under `platformdirs.user_cache_dir("invoke-toolkit") / "tasks" / REPOSITORY_HASH`. The hash identifies the Git root path; outside Git, the shared subdirectory is `no-repo`. Keys use the function name, configured prefix and `repr` of arguments/keyword values; the first positional context is excluded. Names listed in `ignore_args` are excluded for positional or keyword arguments. Long keys are SHA-256 hashed. Function source, loaded configuration, environment, file contents and remote state are **not automatically fingerprinted**.

A cache hit skips the cached task body and returns its stored result; `autoprint` can render it again. `None` results are not stored. Exceptions are not results to cache. Current wrappers catch broad exceptions and can retry the task body after an error, so only cache pure/idempotent work—never rely on exactly-once side effects. Non-None return values must be suitable for diskcache serialization, and cache files/results should be treated as local sensitive data, not a safe untrusted interchange format.

Use TTLs or change `key_prefix` when code/input meaning changes. Exclude an argument only if it cannot affect the return value. Same-named functions can collide unless given distinct prefixes. A [Field](fields.md) is materialized before the cache is consulted; its factory/resolver still executes on a hit. Managed temporary filenames make poor keys, and managed Paths are not durable cached results.

`cache_stats()` reports availability, directory, entry count and disk volume. `clear_task_cache()` clears all entries in the current repository cache. `clear_task_cache(name)` selects short keys by string prefix; it cannot recover a task identity from hashed long keys. Use full cache clearing when that limitation matters. Task-cache clearing does **not** clear completion entries.

Origins: [#51](https://github.com/D3f0/invoke-toolkit/pull/51), async results [#121](https://github.com/D3f0/invoke-toolkit/pull/121), Field key materialization [#128](https://github.com/D3f0/invoke-toolkit/pull/128).

## Completion callback cache

Shell completion often runs a new Python process per request, so `functools.lru_cache` does not persist suggestions between requests. Toolkit's `@cached(ttl=300.0, maxsize=None)` persists callback results with diskcache.

Save this alternative complete `tasks.py`:

```python
from typing import Annotated

from invoke_toolkit import Context, cached, task


@cached(ttl=60, maxsize=1024 * 1024)
def complete_docs_target(ctx: Context, incomplete: str) -> list[str]:
    targets = ctx.get_config_value("docs.targets", default=["staging", "production"])
    return sorted(target for target in targets if target.startswith(incomplete))


@task
def describe(
    ctx: Context,
    target: Annotated[str, complete_docs_target] = "staging",
) -> None:
    print(target)


@task
def completion_cache_info(ctx: Context) -> None:
    ctx.print(complete_docs_target.cache_info())


@task
def clear_completion_cache(ctx: Context) -> None:
    complete_docs_target.cache_clear()
```

```bash
intk --complete -- intk describe --target
intk completion-cache-info
intk clear-completion-cache
```

Completion entries are stored in a `completions` subdirectory of the same repository-specific cache directory. `maxsize` is the diskcache size limit in **bytes**, not a number of suggestions. The key is the callback's function name plus the exact `incomplete` string, not its `Context`, project config, source or environment. Keep names unique and use a TTL/clear after configuration changes. Never persist secret suggestions. `cache_clear()` removes this callback's short-prefix keys; hashed long keys have the same identity limitation. `cache_info()` reports backend/options and disk information when available.

The callback timeout is a separate [completion setting](../humans/completion.md): default `completion.callback_timeout=10.0`, overridable through `INVOKE_COMPLETION_CALLBACK_TIMEOUT`. A timeout is not cache expiry or cancellation of the callback thread. Callback purity and operation-level timeouts still matter.

Origin: [#76](https://github.com/D3f0/invoke-toolkit/pull/76); loaded callback configuration [#101](https://github.com/D3f0/invoke-toolkit/pull/101).
