"""
Task caching functionality using diskcache as backend.

Provides optional caching for task results with:
- Automatic cache location based on git repository root + platformdirs
- TTL (time-to-live) support
- Debug logging for cache hits/misses
- Graceful degradation when diskcache is not installed
"""

import hashlib
import subprocess
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

import platformdirs
from invoke.util import debug

F = TypeVar("F", bound=Callable[..., Any])

# Check if diskcache is available
try:
    import diskcache

    DISKCACHE_AVAILABLE = True
except ImportError:
    diskcache = None  # type: ignore[assignment]
    DISKCACHE_AVAILABLE = False


@dataclass
class CacheConfig:
    """Configuration for task caching."""

    enabled: bool = True
    ttl: Optional[float] = None  # Time-to-live in seconds, None means no expiration
    key_prefix: str = ""  # Optional prefix for cache keys
    ignore_args: list[str] = field(
        default_factory=list
    )  # Arguments to exclude from cache key


def get_git_root() -> Optional[Path]:
    """
    Get the root directory of the current git repository.

    Returns:
        Path to git root directory, or None if not in a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def get_cache_directory() -> Path:
    """
    Compute the cache directory for invoke-toolkit tasks.

    The cache location is computed as:
    - platformdirs user_cache_dir / "invoke-toolkit" / git_repo_hash

    If not in a git repository, uses a generic "no-repo" subdirectory.

    Returns:
        Path to the cache directory.
    """
    base_cache = Path(platformdirs.user_cache_dir("invoke-toolkit"))
    cache_subdir = "tasks"

    git_root = get_git_root()
    if git_root:
        # Create a hash of the git root path to avoid conflicts
        repo_hash = hashlib.md5(str(git_root).encode()).hexdigest()[:12]
        cache_dir = base_cache / cache_subdir / repo_hash
    else:
        cache_dir = base_cache / cache_subdir / "no-repo"

    return cache_dir


def make_cache_key(
    func_name: str, args: tuple, kwargs: dict, ignore_args: list[str]
) -> str:
    """
    Create a cache key from function name and arguments.

    Args:
        func_name: Name of the function being cached.
        args: Positional arguments (excluding context which is first arg).
        kwargs: Keyword arguments.
        ignore_args: List of argument names to exclude from cache key.

    Returns:
        A string cache key.
    """
    # Filter out ignored arguments from kwargs
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ignore_args}

    # Create a deterministic string representation
    key_parts = [func_name]

    # Add positional args (skip first arg which is context)
    if args:
        for arg in args:
            key_parts.append(repr(arg))

    # Add sorted kwargs for determinism
    for k in sorted(filtered_kwargs.keys()):
        key_parts.append(f"{k}={filtered_kwargs[k]!r}")

    key_string = ":".join(key_parts)

    # Hash if too long
    if len(key_string) > 200:
        return hashlib.sha256(key_string.encode()).hexdigest()

    return key_string


def get_cache(cache_dir: Optional[Path] = None) -> Optional["diskcache.Cache"]:
    """
    Get or create the diskcache Cache instance.

    Args:
        cache_dir: Optional custom cache directory. If None, uses default.

    Returns:
        A diskcache.Cache instance, or None if diskcache is not available.
    """
    if not DISKCACHE_AVAILABLE:
        return None

    if cache_dir is None:
        cache_dir = get_cache_directory()

    cache_dir.mkdir(parents=True, exist_ok=True)
    return diskcache.Cache(str(cache_dir))


def cached_task_wrapper(
    func: F,
    config: CacheConfig,
) -> F:
    """
    Wrap a task function with caching logic.

    Args:
        func: The original task function.
        config: Cache configuration.

    Returns:
        Wrapped function with caching.
    """
    if not config.enabled:
        return func

    func_name = getattr(func, "__name__", repr(func))

    if not DISKCACHE_AVAILABLE:
        debug(f"diskcache not installed, caching disabled for {func_name}")
        return func

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get or create cache
        cache = get_cache()
        if cache is None:
            debug(f"Could not create cache for {func_name}, running without cache")
            return func(*args, **kwargs)

        try:
            # Create cache key (skip first arg which is context)
            cache_args = args[1:] if args else ()
            key = make_cache_key(
                func_name=f"{config.key_prefix}{func_name}",
                args=cache_args,
                kwargs=kwargs,
                ignore_args=config.ignore_args,
            )

            # Try to get from cache
            result = cache.get(key, default=None)
            if result is not None:
                debug(f"Cache HIT for {func_name} (key: {key[:50]}...)")
                return result

            debug(f"Cache MISS for {func_name} (key: {key[:50]}...)")

            # Execute function and cache result
            result = func(*args, **kwargs)

            # Only cache non-None results
            if result is not None:
                cache.set(key, result, expire=config.ttl)
                debug(f"Cached result for {func_name} (ttl: {config.ttl})")

            return result
        except Exception as e:  # pylint: disable=broad-exception-caught
            # On any cache error, just run the function
            debug(f"Cache error for {func_name}: {e}, running without cache")
            return func(*args, **kwargs)
        finally:
            cache.close()

    return wrapper  # type: ignore[return-value]


def parse_cache_config(
    cache_param: Union[bool, dict, CacheConfig, None],
) -> Optional[CacheConfig]:
    """
    Parse the cache parameter into a CacheConfig.

    Args:
        cache_param: The cache parameter from the @task decorator.
            - True: Enable caching with defaults
            - False/None: Disable caching
            - dict: Enable with custom settings (ttl, key_prefix, ignore_args)
            - CacheConfig: Use as-is

    Returns:
        CacheConfig instance or None if caching should be disabled.
    """
    if cache_param is None or cache_param is False:
        return None

    if isinstance(cache_param, CacheConfig):
        return cache_param

    if cache_param is True:
        return CacheConfig()

    if isinstance(cache_param, dict):
        return CacheConfig(
            enabled=cache_param.get("enabled", True),
            ttl=cache_param.get("ttl"),
            key_prefix=cache_param.get("key_prefix", ""),
            ignore_args=cache_param.get("ignore_args", []),
        )

    return None


def clear_task_cache(task_name: Optional[str] = None) -> int:
    """
    Clear the task cache.

    Args:
        task_name: If provided, only clear cache entries for this task.
                   If None, clear all task cache entries.

    Returns:
        Number of entries cleared.
    """
    if not DISKCACHE_AVAILABLE:
        debug("diskcache not installed, nothing to clear")
        return 0

    cache = get_cache()
    if cache is None:
        return 0

    try:
        if task_name is None:
            # Clear all
            count = len(cache)
            cache.clear()
            debug(f"Cleared {count} cache entries")
            return count

        # Clear entries for specific task
        count = 0
        keys_to_delete = []
        for key in cache.iterkeys():
            if isinstance(key, str) and key.startswith(task_name):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del cache[key]
            count += 1

        debug(f"Cleared {count} cache entries for task {task_name}")
        return count
    finally:
        cache.close()


def cache_stats() -> dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache statistics.
    """
    if not DISKCACHE_AVAILABLE:
        return {"available": False}

    cache = get_cache()
    if cache is None:
        return {"available": False}

    try:
        stats = {
            "available": True,
            "directory": str(cache.directory),
            "size": len(cache),
            "volume": cache.volume(),
        }
        return stats
    finally:
        cache.close()
