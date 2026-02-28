"""
Autocomplete utilities for task completion callbacks.

This module provides utilities for creating completion callbacks that can be
used with task parameters via Annotated type hints.
"""

import hashlib
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from invoke import Context
from invoke.util import debug

# Check if diskcache is available
try:
    import diskcache

    DISKCACHE_AVAILABLE = True
except ImportError:
    diskcache = None  # type: ignore[assignment]
    DISKCACHE_AVAILABLE = False

# Import cache directory helper from cache module
from .cache import get_cache_directory

# Type variable for the callback function
F = TypeVar("F", bound=Callable[[Context, str], list[str]])


def cached(  # pylint: disable=too-many-statements
    ttl: float = 300.0,
    maxsize: Optional[int] = None,
) -> Callable[[F], F]:
    """
    Decorator for caching completion callback results using persistent disk cache.

    This decorator uses diskcache to cache completion callback results across
    separate process invocations. This is essential for shell completion, where
    each completion request happens in a new process.

    **Important**: This decorator requires the `diskcache` package to be installed.
    Install with: `pip install invoke-toolkit[cache]` or `pip install diskcache`

    If diskcache is not available, the decorator will log a warning and the
    callback will execute without caching (but will still work).

    Args:
        ttl: Time-to-live in seconds for cached items (default: 300 = 5 minutes).
             Set to None for no expiration (not recommended for completion data).
        maxsize: Maximum number of cache entries. If None (default), no size limit.
                 The cache may evict old entries automatically based on disk space.

    Returns:
        Decorated callback function with persistent caching

    Example:
        Basic usage with git branches:
        ```python
        from invoke_toolkit import task, Context, cached
        from typing import Annotated

        @cached(ttl=60)  # Cache for 1 minute
        def complete_branches(ctx: Context, incomplete: str) -> list[str]:
            '''Completion callback with cached git branch fetching.'''
            # This expensive operation is cached
            result = ctx.run("git branch --list", hide=True)
            branches = [
                line.strip().lstrip("* ")
                for line in result.stdout.splitlines()
            ]

            # Filter by incomplete prefix
            if incomplete:
                branches = [b for b in branches if b.startswith(incomplete)]

            return sorted(branches)

        @task
        def checkout(ctx: Context, branch: Annotated[str, complete_branches]):
            '''Checkout a git branch with cached completion.'''
            ctx.run(f"git checkout {branch}")
        ```

    Example with API calls:
        ```python
        from invoke_toolkit import cached
        import requests

        @cached(ttl=300)  # Cache for 5 minutes
        def complete_deployments(ctx: Context, incomplete: str) -> list[str]:
            '''Completion callback with cached API data.'''
            # Expensive API call - cached after first invocation
            response = requests.get("https://api.example.com/deployments")
            targets = [d["name"] for d in response.json()]

            if incomplete:
                targets = [t for t in targets if t.startswith(incomplete)]

            return sorted(targets)

        @task
        def deploy(ctx: Context, target: Annotated[str, complete_deployments]):
            '''Deploy to target with cached completion.'''
            ctx.run(f"./deploy.sh {target}")
        ```

    Example with different TTL values:
        ```python
        # Short TTL for frequently changing data
        @cached(ttl=30)  # 30 seconds
        def complete_active_users(ctx: Context, incomplete: str) -> list[str]:
            return fetch_active_users()

        # Longer TTL for stable data
        @cached(ttl=3600)  # 1 hour
        def complete_aws_regions(ctx: Context, incomplete: str) -> list[str]:
            return ["us-east-1", "us-west-2", "eu-west-1"]

        # Very long TTL for static data
        @cached(ttl=86400)  # 24 hours
        def complete_timezones(ctx: Context, incomplete: str) -> list[str]:
            import zoneinfo
            return sorted(zoneinfo.available_timezones())
        ```

    Caching Backend:
        - Uses diskcache for persistent disk-based cache
        - Cache survives process restarts (essential for shell completion)
        - Cache location: ~/.cache/invoke-toolkit/completions/
        - Thread-safe and process-safe

    Thread Safety:
        Completion callbacks are executed in a separate thread with a timeout
        (default: 10 seconds, configurable via INVOKE_COMPLETION_CALLBACK_TIMEOUT).
        Diskcache is thread-safe and process-safe by design.

    Cache Control:
        - TTL ensures stale data is automatically expired
        - Cache can be manually cleared using callback.cache_clear()
        - Cache statistics available via callback.cache_info()
        - Cache persists across process restarts

    Performance Note:
        Shell completion happens in separate processes, so in-memory caching
        (like functools.lru_cache) provides no benefit. This decorator uses
        persistent disk caching which works across process boundaries.
    """
    if not DISKCACHE_AVAILABLE:
        debug(
            "diskcache is not installed. Completion callbacks will run without caching. "
            "Install with: pip install invoke-toolkit[cache]"
        )

    def decorator(func: F) -> F:
        func_name = getattr(func, "__name__", repr(func))

        # Setup disk cache if available
        disk_cache: Optional[Any] = None
        if DISKCACHE_AVAILABLE:
            try:
                cache_dir = get_cache_directory() / "completions"
                cache_dir.mkdir(parents=True, exist_ok=True)
                # Create cache with size limit if specified
                if maxsize is not None:
                    disk_cache = diskcache.Cache(str(cache_dir), size_limit=maxsize)
                else:
                    disk_cache = diskcache.Cache(str(cache_dir))
                debug(f"Using diskcache for completion callback: {func_name}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                debug(f"Failed to initialize diskcache for {func_name}: {e}")
                disk_cache = None

        def _make_cache_key(incomplete: str) -> str:
            """Create a cache key from function name and incomplete string."""
            key_string = f"{func_name}:{incomplete}"
            # Hash if too long for diskcache
            if len(key_string) > 200:
                return hashlib.sha256(key_string.encode()).hexdigest()
            return key_string

        @wraps(func)
        def wrapper(ctx: Context, incomplete: str) -> list[str]:
            cache_key = _make_cache_key(incomplete)

            # Try disk cache if available
            if disk_cache is not None:
                try:
                    result = disk_cache.get(cache_key, default=None)
                    if result is not None:
                        debug(f"Cache HIT (disk) for {func_name} ({cache_key[:50]}...)")
                        return result
                except Exception as e:  # pylint: disable=broad-exception-caught
                    debug(f"Disk cache read error for {func_name}: {e}")

            # Cache miss - call the function
            debug(f"Cache MISS for {func_name} ({cache_key[:50]}...)")
            result = func(ctx, incomplete)

            # Store in disk cache if available
            if disk_cache is not None:
                try:
                    disk_cache.set(cache_key, result, expire=ttl)
                    debug(
                        f"Cached result (disk) for {func_name} (ttl: {ttl}s, key: {cache_key[:50]}...)"
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    debug(f"Disk cache write error for {func_name}: {e}")

            return result

        # Add cache control methods
        def cache_clear() -> None:
            """Clear the cache for this completion callback."""
            if disk_cache is not None:
                try:
                    # Clear only keys for this function
                    keys_to_delete = []
                    for key in disk_cache.iterkeys():
                        if isinstance(key, str) and key.startswith(f"{func_name}:"):
                            keys_to_delete.append(key)
                    for key in keys_to_delete:
                        del disk_cache[key]
                    debug(
                        f"Cleared {len(keys_to_delete)} disk cache entries for {func_name}"
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    debug(f"Error clearing disk cache for {func_name}: {e}")
            else:
                debug(f"Cannot clear cache for {func_name}: diskcache is not available")

        def cache_info() -> dict[str, Any]:
            """Get cache statistics."""
            info: dict[str, Any] = {
                "function": func_name,
                "ttl": ttl,
                "maxsize": maxsize,
                "backend": "diskcache" if disk_cache is not None else "none",
            }

            if disk_cache is not None:
                try:
                    # Count entries for this function
                    entry_count = sum(
                        1
                        for key in disk_cache.iterkeys()
                        if isinstance(key, str) and key.startswith(f"{func_name}:")
                    )
                    info["entries"] = entry_count
                    info["total_size"] = len(disk_cache)
                    info["disk_volume"] = disk_cache.volume()
                    info["cache_directory"] = str(disk_cache.directory)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    debug(f"Error getting cache info for {func_name}: {e}")

            return info

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        wrapper.cache_info = cache_info  # type: ignore[attr-defined]

        # Store reference to cache for testing
        wrapper._disk_cache = disk_cache  # type: ignore[attr-defined]  # pylint: disable=protected-access

        return cast(F, wrapper)

    return decorator
