"""SQLite response cache.

Keyed by a stable hash of normalized request params, so re-running an
identical audit costs zero SerpApi credits. WAL mode + a per-connection
lock make concurrent reads/writes from multiple asyncio tasks (or
processes) safe without a heavier dependency.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .exceptions import CacheError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache (expires_at);
"""


def make_cache_key(kind: str, params: dict[str, Any]) -> str:
    """Hash a normalized params dict into a stable cache key.

    `kind` namespaces the key (e.g. "search" vs "trends") so the two
    call types never collide even with overlapping param names.
    """
    normalized = json.dumps(params, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{kind}:{digest}"


class SQLiteCache:
    """Thread-safe TTL cache over a single SQLite file."""

    def __init__(
        self,
        path: str | Path = "biaslens_cache.sqlite3",
        *,
        default_ttl: float = 30 * 24 * 3600,
    ) -> None:
        self._path = str(path)
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        try:
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        except sqlite3.Error as exc:  # pragma: no cover - environment-dependent
            raise CacheError(f"Failed to open cache at {self._path}: {exc}") from exc

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT payload, expires_at FROM cache WHERE key = ?", (key,)
                ).fetchone()
            except sqlite3.Error as exc:  # pragma: no cover
                raise CacheError(f"Cache read failed: {exc}") from exc
        if row is None:
            return None
        payload, expires_at = row
        if expires_at < time.time():
            self.delete(key)
            return None
        result: dict[str, Any] = json.loads(payload)
        return result

    def set(self, key: str, value: dict[str, Any], *, ttl: float | None = None) -> None:
        now = time.time()
        expires_at = now + (ttl if ttl is not None else self._default_ttl)
        payload = json.dumps(value, default=str)
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO cache (key, payload, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, "
                    "created_at=excluded.created_at, expires_at=excluded.expires_at",
                    (key, payload, now, expires_at),
                )
                self._conn.commit()
            except sqlite3.Error as exc:  # pragma: no cover
                raise CacheError(f"Cache write failed: {exc}") from exc

    def delete(self, key: str) -> None:
        with self._lock:
            try:
                self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._conn.commit()
            except sqlite3.Error as exc:  # pragma: no cover
                raise CacheError(f"Cache delete failed: {exc}") from exc

    def stats(self) -> dict[str, int]:
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            expired = self._conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at < ?", (time.time(),)
            ).fetchone()[0]
        return {"total_entries": total, "expired_entries": expired, "live_entries": total - expired}

    def purge_expired(self) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
            self._conn.commit()
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> SQLiteCache:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
