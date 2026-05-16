"""Tests for the market data cache layer."""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime, timezone

import pytest

from src.data.cache.market_cache import InMemoryCache, MarketData, SQLiteCache


@pytest.fixture
def sample_data() -> list[MarketData]:
    """Return a small list of ``MarketData`` objects for testing."""
    return [
        MarketData(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc).isoformat(),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        ),
        MarketData(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc).isoformat(),
            open=100.5,
            high=102.0,
            low=100.0,
            close=101.5,
            volume=1500.0,
        ),
    ]


@pytest.fixture
def temp_db_path() -> str:
    """Yield a temporary file path and clean it up after the test."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_cache_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestInMemoryCache:
    """Unit tests for the synchronous in-memory cache."""

    def test_get_missing_key_returns_none(self) -> None:
        cache = InMemoryCache()
        assert cache.get("missing") is None

    def test_set_and_get(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data)
        result = cache.get("aapl")
        assert result is not None
        assert len(result) == len(sample_data)
        assert result[0].symbol == "AAPL"
        assert result[0].close == 100.5

    def test_overwrite_existing_key(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data)
        new_data = [
            MarketData(
                symbol="TSLA",
                timestamp=datetime.now(timezone.utc).isoformat(),
                open=200.0,
                high=205.0,
                low=198.0,
                close=204.0,
                volume=5000.0,
            ),
        ]
        cache.set("aapl", new_data)
        result = cache.get("aapl")
        assert result is not None
        assert result[0].symbol == "TSLA"

    def test_invalidate_removes_key(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data)
        cache.invalidate("aapl")
        assert cache.get("aapl") is None

    def test_clear_removes_all_keys(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data)
        cache.set("tsla", sample_data)
        cache.clear()
        assert cache.get("aapl") is None
        assert cache.get("tsla") is None

    def test_ttl_expiration(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data, ttl=1)
        assert cache.get("aapl") is not None
        # Wait for TTL to expire
        import time

        time.sleep(1.1)
        assert cache.get("aapl") is None

    def test_no_ttl_means_no_expiration(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data)
        assert cache.get("aapl") is not None

    def test_zero_ttl_treated_as_no_expiration(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data, ttl=0)
        assert cache.get("aapl") is not None

    def test_cleanup_expired_eagerly(self, sample_data: list[MarketData]) -> None:
        cache = InMemoryCache()
        cache.set("aapl", sample_data, ttl=1)
        import time

        time.sleep(1.1)
        cache._cleanup_expired()
        assert "aapl" not in cache._store


@pytest.mark.asyncio
class TestSQLiteCache:
    """Async unit tests for the SQLite-backed cache."""

    async def test_get_missing_key_returns_none(self, temp_db_path: str) -> None:
        cache = SQLiteCache(temp_db_path)
        assert await cache.get("missing") is None

    async def test_set_and_get(self, temp_db_path: str, sample_data: list[MarketData]) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data)
        result = await cache.get("aapl")
        assert result is not None
        assert len(result) == len(sample_data)
        assert result[0].symbol == "AAPL"
        assert result[0].close == 100.5

    async def test_overwrite_existing_key(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data)
        new_data = [
            MarketData(
                symbol="TSLA",
                timestamp=datetime.now(timezone.utc).isoformat(),
                open=200.0,
                high=205.0,
                low=198.0,
                close=204.0,
                volume=5000.0,
            ),
        ]
        await cache.set("aapl", new_data)
        result = await cache.get("aapl")
        assert result is not None
        assert result[0].symbol == "TSLA"

    async def test_invalidate_removes_key(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data)
        await cache.invalidate("aapl")
        assert await cache.get("aapl") is None

    async def test_clear_removes_all_keys(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data)
        await cache.set("tsla", sample_data)
        await cache.clear()
        assert await cache.get("aapl") is None
        assert await cache.get("tsla") is None

    async def test_ttl_expiration(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data, ttl=1)
        assert await cache.get("aapl") is not None
        await asyncio.sleep(1.1)
        assert await cache.get("aapl") is None

    async def test_no_ttl_means_no_expiration(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data)
        assert await cache.get("aapl") is not None

    async def test_zero_ttl_treated_as_no_expiration(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data, ttl=0)
        assert await cache.get("aapl") is not None

    async def test_data_survives_reopen(
        self, temp_db_path: str, sample_data: list[MarketData]
    ) -> None:
        cache = SQLiteCache(temp_db_path)
        await cache.set("aapl", sample_data)
        # Simulate process restart by creating a new instance pointing to the same file
        cache2 = SQLiteCache(temp_db_path)
        result = await cache2.get("aapl")
        assert result is not None
        assert len(result) == len(sample_data)
