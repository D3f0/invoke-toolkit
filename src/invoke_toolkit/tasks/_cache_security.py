"""Machine-local cache authentication; no untrusted pickle reaches a decoder."""

import hmac
import os
import pickle
import sqlite3
import stat
import tempfile
from pathlib import Path
from typing import Any, Literal

import diskcache
from diskcache.core import DEFAULT_SETTINGS, ENOVAL, METADATA, MODE_RAW

_MAGIC = b"intk-cache-hmac-v1\0"
_MISSING = object()


def load_cache_key(state_directory: Path) -> bytes:
    """Read an owner-only key, atomically creating it outside the cache store."""
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory_stat = state_directory.lstat()
    if (
        not stat.S_ISDIR(directory_stat.st_mode)
        or directory_stat.st_uid != os.getuid()
        or directory_stat.st_mode & 0o077
    ):
        raise OSError(
            "Cache signing directory must be owned by the user with mode 0700"
        )
    key_path = state_directory / "cache.key"
    if not key_path.exists():
        fd, temporary = tempfile.mkstemp(dir=state_directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(os.urandom(32))
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, key_path)
            except FileExistsError:
                pass  # Another process published its complete key first.
        finally:
            os.unlink(temporary)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(key_path, flags)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise OSError("Cache signing key must be an owner-only regular file")
        key = os.read(fd, 33)
        if len(key) != 32:
            raise OSError("Cache signing key must contain exactly 32 bytes")
        return key
    finally:
        os.close(fd)


# Exact built-in types keep subclass hooks out of the raw storage boundary.
class _BytesDisk(diskcache.Disk):
    """Only inline bytes and raw string keys; never use Disk's pickle paths."""

    # pylint: disable=unidiomatic-typecheck

    def put(self, key: str) -> tuple[str, Literal[True]]:
        if type(key) is not str:
            raise ValueError("Cache keys must be strings")
        return key, True

    def get(self, key: Any, raw: bool) -> str:
        if not raw or type(key) is not str:
            raise ValueError("Rejecting a serialized cache key")
        return key

    def store(
        self, value: bytes, read: bool, key: Any = None
    ) -> tuple[Literal[0], Literal[1], None, memoryview]:
        if read or type(value) is not bytes:
            raise ValueError("Cache storage requires an authenticated byte envelope")
        return 0, MODE_RAW, None, sqlite3.Binary(value)

    def fetch(self, mode: int, filename: str | None, value: Any, read: bool) -> bytes:
        # Inline-only storage also prevents attacker-controlled file paths.
        if read or mode != MODE_RAW or filename is not None or type(value) is not bytes:
            raise OSError("Rejecting an unsigned or unsupported cache entry")
        return value

    def remove(self, file_path: str) -> None:
        """Never delete files named by unauthenticated database rows.

        This backend only writes inline values. Legacy spill files are left
        untouched; removing them safely is not part of reading this cache.
        """
        return None


class AuthenticatedCache(diskcache.Cache):
    """Authenticate directory, lookup key and serialized value before unpickling."""

    def __init__(self, directory: str, secret: bytes, **settings: Any) -> None:
        super().__init__(directory, disk=_BytesDisk, **settings)
        self._secret = secret
        self._context = _MAGIC + os.fsencode(str(Path(directory).resolve())) + b"\0"

    def reset(self, key: str, value: Any = ENOVAL, update: bool = True) -> Any:
        """Do not let persisted settings replace methods or private state."""
        if key not in DEFAULT_SETTINGS and key not in METADATA:
            return None
        return super().reset(key, value, update)

    def _message(self, key: str, payload: bytes) -> bytes:
        encoded = key.encode("utf-8")
        return self._context + len(encoded).to_bytes(8, "big") + encoded + payload

    def set(self, key: str, value: Any, expire=None, read=False, tag=None, retry=False):
        if read:
            raise ValueError("File handles are not supported by authenticated caches")
        payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        signature = hmac.digest(self._secret, self._message(key, payload), "sha256")
        return super().set(key, _MAGIC + signature + payload, expire, False, tag, retry)

    def get(
        self,
        key: str,
        default=None,
        read=False,
        expire_time=False,
        tag=False,
        retry=False,
    ):
        if read:
            raise ValueError("File handles are not supported by authenticated caches")
        result: Any = super().get(key, _MISSING, False, expire_time, tag, retry)
        envelope = result[0] if expire_time or tag else result
        metadata = result[1:] if expire_time or tag else ()
        value = default
        if isinstance(envelope, bytes) and envelope.startswith(_MAGIC):
            offset = len(_MAGIC)
            signature, payload = envelope[offset : offset + 32], envelope[offset + 32 :]
            expected = hmac.digest(self._secret, self._message(key, payload), "sha256")
            if hmac.compare_digest(signature, expected):
                value = pickle.loads(payload)
        return (value, *metadata) if expire_time or tag else value
