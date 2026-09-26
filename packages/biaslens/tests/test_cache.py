import time
from pathlib import Path

from biaslens.cache import SQLiteCache, make_cache_key


def test_make_cache_key_is_stable_and_order_independent() -> None:
    k1 = make_cache_key("search", {"a": 1, "b": 2})
    k2 = make_cache_key("search", {"b": 2, "a": 1})
    assert k1 == k2
    assert k1.startswith("search:")


def test_make_cache_key_namespaces_by_kind() -> None:
    k1 = make_cache_key("search", {"q": "x"})
    k2 = make_cache_key("trends", {"q": "x"})
    assert k1 != k2


def test_set_and_get_roundtrip(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    cache.set("k1", {"foo": "bar"})
    assert cache.get("k1") == {"foo": "bar"}
    cache.close()


def test_missing_key_returns_none(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    assert cache.get("does-not-exist") is None
    cache.close()


def test_ttl_expiry(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    cache.set("k1", {"foo": "bar"}, ttl=0.05)
    assert cache.get("k1") == {"foo": "bar"}
    time.sleep(0.1)
    assert cache.get("k1") is None
    cache.close()


def test_stats_and_purge(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    cache.set("k1", {"a": 1}, ttl=0.05)
    cache.set("k2", {"a": 2}, ttl=1000)
    time.sleep(0.1)
    stats = cache.stats()
    assert stats["total_entries"] == 2
    assert stats["expired_entries"] == 1
    purged = cache.purge_expired()
    assert purged == 1
    assert cache.stats()["total_entries"] == 1
    cache.close()


def test_context_manager_closes(tmp_path: Path) -> None:
    with SQLiteCache(tmp_path / "c.sqlite3") as cache:
        cache.set("k", {"v": 1})
        assert cache.get("k") == {"v": 1}
