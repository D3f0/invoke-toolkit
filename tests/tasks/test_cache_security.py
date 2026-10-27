"""Cache readers must authenticate attacker-controlled bytes before unpickling."""

import asyncio
import sqlite3
from pathlib import Path

import pytest

from invoke.context import Context
from invoke_toolkit.tasks import autocomplete
from invoke_toolkit.tasks import cache as task_cache


diskcache = pytest.importorskip("diskcache")


class Poison:  # pylint: disable=too-few-public-methods
    def __init__(self, marker: Path):
        self.marker = marker

    def __reduce__(self):
        return eval, (f"__import__('pathlib').Path({str(self.marker)!r}).touch()",)


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        task_cache.platformdirs, "user_data_dir", lambda *a: str(tmp_path / "state")
    )
    monkeypatch.setattr(task_cache, "get_cache_directory", lambda: tmp_path / "cache")
    monkeypatch.setattr(autocomplete, "get_cache_directory", lambda: tmp_path / "cache")
    return tmp_path / "cache"


@pytest.mark.parametrize(
    "reader", ["task", "async-task", "completion", "key-iteration"]
)
@pytest.mark.parametrize("storage", ["inline", "file"])
def test_unsigned_pickle_never_executes(isolated_cache, tmp_path, reader, storage):
    marker = tmp_path / "executed"
    directory = (
        isolated_cache / "completions" if reader == "completion" else isolated_cache
    )
    with diskcache.Cache(
        str(directory), disk_min_file_size=0 if storage == "file" else 2**20
    ) as planted:
        if reader == "key-iteration":
            planted.set(Poison(marker), "value")
        else:
            key = {
                "task": "produce_task",
                "async-task": "produce_async",
                "completion": "produce_completion:",
            }[reader]
            planted.set(key, Poison(marker))

    if reader == "key-iteration":
        with pytest.raises((ValueError, OSError)):
            task_cache.clear_task_cache("produce")
    elif reader == "completion":

        @autocomplete.cached()
        def produce_completion(ctx: Context, incomplete: str) -> list[str]:
            return ["safe"]

        try:
            assert produce_completion(Context(), "") == ["safe"]
        finally:
            getattr(produce_completion, "_disk_cache").close()
    elif reader == "async-task":

        async def produce_async(ctx: Context) -> dict[str, bool]:
            return {"safe": True}

        wrapped = task_cache.cached_task_wrapper(
            produce_async, task_cache.CacheConfig()
        )
        assert asyncio.run(wrapped(Context())) == {"safe": True}
    else:

        def produce_task(ctx: Context) -> dict[str, bool]:
            return {"safe": True}

        wrapped = task_cache.cached_task_wrapper(produce_task, task_cache.CacheConfig())
        assert wrapped(Context()) == {"safe": True}
    assert not marker.exists()


def test_tampered_authenticated_value_is_recomputed(isolated_cache):
    calls = []

    def produce(ctx):
        calls.append(1)
        return {"items": ("safe", b"bytes")}

    wrapped = task_cache.cached_task_wrapper(produce, task_cache.CacheConfig())
    expected = {"items": ("safe", b"bytes")}
    assert wrapped(Context()) == expected
    assert wrapped(Context()) == expected
    assert calls == [1]
    with sqlite3.connect(isolated_cache / "cache.db") as connection:
        rowid, value = connection.execute("SELECT rowid, value FROM Cache").fetchone()
        changed = bytes(value[:-1]) + bytes([value[-1] ^ 1])
        connection.execute(
            "UPDATE Cache SET value = ? WHERE rowid = ?", (changed, rowid)
        )
    assert wrapped(Context()) == expected
    assert calls == [1, 1]


def test_authenticated_values_cannot_move_between_keys_or_caches(
    isolated_cache, tmp_path
):
    cache = task_cache.get_cache(isolated_cache)
    assert cache is not None
    with cache:
        cache.set("original", {"secret": "value"})  # pragma: allowlist secret
    with sqlite3.connect(isolated_cache / "cache.db") as connection:
        value = connection.execute(
            "SELECT value FROM Cache WHERE key = 'original'"
        ).fetchone()[0]
    for directory, key in (
        (isolated_cache, "different"),
        (tmp_path / "other", "original"),
    ):
        cache = task_cache.get_cache(directory)
        assert cache is not None
        with cache:
            cache.set(key, "placeholder")
            with sqlite3.connect(directory / "cache.db") as connection:
                connection.execute(
                    "UPDATE Cache SET value = ? WHERE key = ?", (value, key)
                )
            assert cache.get(key, default="miss") == "miss"


@pytest.mark.parametrize("target", ["directory", "key"])
def test_insecure_signing_state_disables_caching(isolated_cache, tmp_path, target):
    cache = task_cache.get_cache(isolated_cache)
    assert cache is not None
    cache.close()
    state = tmp_path / "state" / "cache-signing"
    path = state if target == "directory" else state / "cache.key"
    path.chmod(0o755 if target == "directory" else 0o644)
    assert task_cache.get_cache(isolated_cache) is None


def test_signing_key_symlink_is_rejected(isolated_cache, tmp_path):
    state = tmp_path / "state" / "cache-signing"
    state.mkdir(parents=True, mode=0o700)
    foreign = tmp_path / "foreign.key"
    foreign.write_bytes(b"x" * 32)
    foreign.chmod(0o600)
    (state / "cache.key").symlink_to(foreign)
    assert task_cache.get_cache(isolated_cache) is None


def test_poisoned_authenticated_payload_never_executes(isolated_cache, tmp_path):
    import pickle

    marker = tmp_path / "executed"
    cache = task_cache.get_cache(isolated_cache)
    assert cache is not None
    with cache:
        cache.set("entry", {"safe": True})
        with sqlite3.connect(isolated_cache / "cache.db") as connection:
            envelope = connection.execute(
                "SELECT value FROM Cache WHERE key = 'entry'"
            ).fetchone()[0]
            malicious = envelope[:50] + pickle.dumps(Poison(marker))
            connection.execute(
                "UPDATE Cache SET value = ? WHERE key = 'entry'", (malicious,)
            )
        assert cache.get("entry", default="miss") == "miss"
    assert not marker.exists()


def test_persisted_settings_cannot_replace_signing_key(isolated_cache, tmp_path):
    import hmac
    import pickle

    marker = tmp_path / "executed"
    attacker_key = b"attacker" * 4  # pragma: allowlist secret
    magic = b"intk-cache-hmac-v1\0"
    payload = pickle.dumps(Poison(marker))
    message = (
        magic
        + str(isolated_cache.resolve()).encode()
        + b"\0"
        + (5).to_bytes(8, "big")
        + b"entry"
        + payload
    )
    forged = magic + hmac.digest(attacker_key, message, "sha256") + payload
    with diskcache.Cache(str(isolated_cache)) as planted:
        planted.set("entry", forged)
    with sqlite3.connect(isolated_cache / "cache.db") as connection:
        connection.execute(
            "INSERT INTO Settings VALUES ('_secret', ?)", (attacker_key,)
        )
    cache = task_cache.get_cache(isolated_cache)
    assert cache is not None
    with cache:
        assert cache.get("entry", default="miss") == "miss"
    assert not marker.exists()


@pytest.mark.parametrize("operation", ["replace", "clear", "delete"])
def test_foreign_cache_filename_never_deletes_user_file(
    isolated_cache, tmp_path, operation
):
    victim = tmp_path / "keep.txt"
    victim.write_text("keep")
    with diskcache.Cache(str(isolated_cache)) as planted:
        planted.set("entry", "old")
    with sqlite3.connect(isolated_cache / "cache.db") as connection:
        connection.execute(
            "UPDATE Cache SET filename = ?, mode = 2, value = NULL", (str(victim),)
        )
    cache = task_cache.get_cache(isolated_cache)
    assert cache is not None
    with cache:
        if operation == "replace":
            cache.set("entry", "safe")
        elif operation == "clear":
            cache.clear()
        else:
            del cache["entry"]
    assert victim.read_text() == "keep"


def test_concurrent_key_publication_accepts_complete_key(tmp_path, monkeypatch):
    from invoke_toolkit.tasks._cache_security import load_cache_key

    state = tmp_path / "state"
    import os

    real_link = os.link
    observed = []

    def publish(source, destination):
        real_link(source, destination)
        observed.append(load_cache_key(state))

    monkeypatch.setattr(os, "link", publish)
    key = load_cache_key(state)
    assert observed == [key]
