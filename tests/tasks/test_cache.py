"""
Tests for task caching functionality.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from invoke_toolkit import Context, task
from invoke_toolkit.tasks.cache import (
    DISKCACHE_AVAILABLE,
    CacheConfig,
    cache_stats,
    cached_task_wrapper,
    clear_task_cache,
    get_cache,
    get_cache_directory,
    get_git_root,
    make_cache_key,
    parse_cache_config,
)

# Tests for get_git_root function


def test_get_git_root_returns_path_in_git_repo(tmp_path: Path):
    """Should return the git root when inside a git repository."""
    # Initialize a git repo in tmp_path
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Change to the tmp_path and check
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=str(tmp_path))
        result = get_git_root()
        assert result is not None
        assert isinstance(result, Path)


def test_get_git_root_returns_none_outside_git_repo():
    """Should return None when not in a git repository."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        result = get_git_root()
        assert result is None


def test_get_git_root_handles_timeout():
    """Should return None on timeout."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)
        result = get_git_root()
        assert result is None


# Tests for get_cache_directory function


def test_get_cache_directory_returns_path():
    """Should return a Path object."""
    cache_dir = get_cache_directory()
    assert isinstance(cache_dir, Path)


def test_get_cache_directory_includes_invoke_toolkit_in_path():
    """Cache directory should include invoke-toolkit."""
    cache_dir = get_cache_directory()
    assert "invoke-toolkit" in str(cache_dir)


def test_get_cache_directory_uses_repo_hash_when_in_git():
    """Should use git repo hash when in a git repository."""
    with patch("invoke_toolkit.tasks.cache.get_git_root") as mock_git_root:
        mock_git_root.return_value = Path("/some/repo/path")
        cache_dir = get_cache_directory()
        # Should not contain "no-repo"
        assert "no-repo" not in str(cache_dir)


def test_get_cache_directory_uses_no_repo_when_outside_git():
    """Should use no-repo subdirectory when not in git."""
    with patch("invoke_toolkit.tasks.cache.get_git_root") as mock_git_root:
        mock_git_root.return_value = None
        cache_dir = get_cache_directory()
        assert "no-repo" in str(cache_dir)


# Tests for make_cache_key function


def test_make_cache_key_basic_key_generation():
    """Should generate a key from function name and args."""
    key = make_cache_key("my_func", ("arg1",), {"kwarg1": "value1"}, [])
    assert "my_func" in key
    assert "arg1" in key
    assert "kwarg1" in key


def test_make_cache_key_ignores_specified_args():
    """Should ignore args in ignore_args list."""
    key = make_cache_key(
        "my_func", (), {"include_me": "yes", "ignore_me": "no"}, ["ignore_me"]
    )
    assert "include_me" in key
    assert "ignore_me" not in key


def test_make_cache_key_deterministic_keys():
    """Same inputs should produce same key."""
    key1 = make_cache_key("func", ("a", "b"), {"x": 1, "y": 2}, [])
    key2 = make_cache_key("func", ("a", "b"), {"x": 1, "y": 2}, [])
    assert key1 == key2


def test_make_cache_key_different_args_different_keys():
    """Different args should produce different keys."""
    key1 = make_cache_key("func", ("a",), {}, [])
    key2 = make_cache_key("func", ("b",), {}, [])
    assert key1 != key2


def test_make_cache_key_long_keys_are_hashed():
    """Keys longer than 200 chars should be hashed."""
    long_arg = "x" * 300
    key = make_cache_key("func", (long_arg,), {}, [])
    # SHA256 hash is 64 chars
    assert len(key) == 64


# Tests for parse_cache_config function


def test_parse_cache_config_none_returns_none():
    """None should return None."""
    assert parse_cache_config(None) is None


def test_parse_cache_config_false_returns_none():
    """False should return None."""
    assert parse_cache_config(False) is None


def test_parse_cache_config_true_returns_default_config():
    """True should return default CacheConfig."""
    config = parse_cache_config(True)
    assert config is not None
    assert config.enabled is True
    assert config.ttl is None


def test_parse_cache_config_dict_with_ttl():
    """Dict with ttl should set ttl."""
    config = parse_cache_config({"ttl": 3600})
    assert config is not None
    assert config.ttl == 3600


def test_parse_cache_config_dict_with_ignore_args():
    """Dict with ignore_args should set ignore_args."""
    config = parse_cache_config({"ignore_args": ["verbose", "debug"]})
    assert config is not None
    assert "verbose" in config.ignore_args
    assert "debug" in config.ignore_args


def test_parse_cache_config_dict_with_key_prefix():
    """Dict with key_prefix should set key_prefix."""
    config = parse_cache_config({"key_prefix": "myapp:"})
    assert config is not None
    assert config.key_prefix == "myapp:"


def test_parse_cache_config_cache_config_passthrough():
    """CacheConfig instance should pass through unchanged."""
    original = CacheConfig(ttl=1800, key_prefix="test:")
    config = parse_cache_config(original)
    assert config is original


# Tests for get_cache function


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_get_cache_returns_cache_instance(tmp_path: Path):
    """Should return a diskcache.Cache instance."""
    cache = get_cache(tmp_path)
    assert cache is not None
    cache.close()


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_get_cache_creates_directory(tmp_path: Path):
    """Should create the cache directory if it doesn't exist."""
    cache_dir = tmp_path / "new_cache_dir"
    cache = get_cache(cache_dir)
    assert cache is not None
    assert cache_dir.exists()
    cache.close()


# Tests for cached_task_wrapper function


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_cached_task_wrapper_caches_result(tmp_path: Path):
    """Should cache function results."""
    call_count = 0

    def my_func(ctx, x):
        nonlocal call_count
        call_count += 1
        return x * 2

    config = CacheConfig()

    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path
        wrapped = cached_task_wrapper(my_func, config)
        ctx = MagicMock()

        # First call - should execute function
        result1 = wrapped(ctx, 5)
        assert result1 == 10
        assert call_count == 1

        # Second call with same args - should use cache
        result2 = wrapped(ctx, 5)
        assert result2 == 10
        assert call_count == 1  # Still 1, cached


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_cached_task_wrapper_different_args_not_cached(tmp_path: Path):
    """Different args should not use cached result."""
    call_count = 0

    def my_func(ctx, x):
        nonlocal call_count
        call_count += 1
        return x * 2

    config = CacheConfig()

    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path
        wrapped = cached_task_wrapper(my_func, config)
        ctx = MagicMock()

        wrapped(ctx, 5)
        assert call_count == 1

        wrapped(ctx, 10)
        assert call_count == 2  # Different arg, new call


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_cached_task_wrapper_disabled_config_no_caching():
    """Disabled config should not wrap function."""

    def my_func(ctx, x):
        return x

    config = CacheConfig(enabled=False)
    wrapped = cached_task_wrapper(my_func, config)

    # Should return original function
    assert wrapped is my_func


# Tests for clear_task_cache function


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_clear_task_cache_clears_all_entries(tmp_path: Path):
    """Should clear all cache entries."""
    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path
        cache = get_cache()
        assert cache is not None
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.close()

        cleared = clear_task_cache()
        assert cleared == 2

        # Verify cache is empty
        cache = get_cache()
        assert cache is not None
        assert len(cache) == 0
        cache.close()


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_clear_task_cache_clears_specific_task(tmp_path: Path):
    """Should clear only entries for specific task."""
    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path
        cache = get_cache()
        assert cache is not None
        cache.set("my_task:arg1", "value1")
        cache.set("my_task:arg2", "value2")
        cache.set("other_task:arg1", "value3")
        cache.close()

        cleared = clear_task_cache("my_task")
        assert cleared == 2

        # Verify only other_task remains
        cache = get_cache()
        assert cache is not None
        assert len(cache) == 1
        cache.close()


# Tests for cache_stats function


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_cache_stats_returns_stats_dict(tmp_path: Path):
    """Should return dictionary with stats."""
    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path
        stats = cache_stats()

        assert isinstance(stats, dict)
        assert stats["available"] is True
        assert "directory" in stats
        assert "size" in stats


# Tests for graceful degradation when diskcache is not installed


def test_get_cache_returns_none_without_diskcache():
    """get_cache should return None when diskcache unavailable."""
    with patch("invoke_toolkit.tasks.cache.DISKCACHE_AVAILABLE", False):
        result = get_cache()
        assert result is None


def test_wrapper_returns_original_without_diskcache():
    """cached_task_wrapper should return original func."""

    def my_func(ctx, x):
        return x

    config = CacheConfig()

    with patch("invoke_toolkit.tasks.cache.DISKCACHE_AVAILABLE", False):
        wrapped = cached_task_wrapper(my_func, config)
        assert wrapped is my_func


def test_clear_cache_returns_zero_without_diskcache():
    """clear_task_cache should return 0 when diskcache unavailable."""
    with patch("invoke_toolkit.tasks.cache.DISKCACHE_AVAILABLE", False):
        result = clear_task_cache()
        assert result == 0


def test_cache_stats_returns_unavailable_without_diskcache():
    """cache_stats should indicate unavailability."""
    with patch("invoke_toolkit.tasks.cache.DISKCACHE_AVAILABLE", False):
        stats = cache_stats()
        assert stats == {"available": False}


# Integration tests for @task decorator with cache parameter


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_task_with_cache_true(ctx: Context, tmp_path: Path):
    """Task with cache=True should cache results."""
    call_count = 0

    @task(cache=True)
    def cached_task(c: Context, value: int) -> int:
        nonlocal call_count
        call_count += 1
        return value * 2

    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path

        # Call the task body directly (simulating invoke behavior)
        result1 = cached_task.body(ctx, 5)
        assert result1 == 10
        assert call_count == 1

        result2 = cached_task.body(ctx, 5)
        assert result2 == 10
        assert call_count == 1  # Cached


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_task_with_cache_ttl(ctx: Context, tmp_path: Path):
    """Task with cache TTL should work."""

    @task(cache={"ttl": 3600})
    def cached_with_ttl(c: Context, value: str) -> str:
        return f"processed: {value}"

    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path

        result = cached_with_ttl.body(ctx, "test")
        assert result == "processed: test"


def test_task_without_cache(ctx: Context):
    """Task without cache parameter should not cache."""
    call_count = 0

    @task
    def uncached_task(c: Context, value: int) -> int:
        nonlocal call_count
        call_count += 1
        return value * 2

    result1 = uncached_task.body(ctx, 5)  # type: ignore[attr-defined]
    result2 = uncached_task.body(ctx, 5)  # type: ignore[attr-defined]

    assert result1 == 10
    assert result2 == 10
    assert call_count == 2  # Called twice, no caching


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_task_with_cache_false(ctx: Context):
    """Task with cache=False should not cache."""
    call_count = 0

    @task(cache=False)
    def no_cache_task(c: Context, value: int) -> int:
        nonlocal call_count
        call_count += 1
        return value * 2

    no_cache_task.body(ctx, 5)
    no_cache_task.body(ctx, 5)

    assert call_count == 2


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_cache_none_result_not_cached(ctx: Context, tmp_path: Path):
    """None results should not be cached."""
    call_count = 0

    @task(cache=True)
    def returns_none(c: Context) -> None:
        nonlocal call_count
        call_count += 1

    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path

        returns_none.body(ctx)
        returns_none.body(ctx)

        # Should be called twice since None is not cached
        assert call_count == 2


@pytest.mark.skipif(not DISKCACHE_AVAILABLE, reason="diskcache not installed")
def test_cache_with_ignore_args(ctx: Context, tmp_path: Path):
    """Cache should ignore specified arguments."""
    call_count = 0

    @task(cache={"ignore_args": ["verbose"]})
    def task_with_verbose(c: Context, query: str, verbose: bool = False) -> str:
        nonlocal call_count
        call_count += 1
        return f"result: {query}"

    with patch("invoke_toolkit.tasks.cache.get_cache_directory") as mock_dir:
        mock_dir.return_value = tmp_path

        result1 = task_with_verbose.body(ctx, "test", verbose=False)
        result2 = task_with_verbose.body(ctx, "test", verbose=True)

        assert result1 == result2
        assert call_count == 1  # Only called once, verbose is ignored
