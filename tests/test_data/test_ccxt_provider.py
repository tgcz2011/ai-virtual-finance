from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.data.models import AssetType, DataInterval, MarketDataRequest
from src.data.providers.ccxt_provider import CCXTProvider, DataProviderError


class TestCCXTProvider:
    """CCXTProvider 单元测试，全部使用 mock 模拟 ccxt exchange。"""

    @pytest.fixture
    def mock_exchange(self) -> MagicMock:
        """返回模拟的 ccxt exchange 对象。"""
        return MagicMock()

    @pytest.fixture
    def provider(self, mock_exchange: MagicMock) -> CCXTProvider:
        """返回注入 mock exchange 的 CCXTProvider 实例。"""
        with patch("src.data.providers.ccxt_provider.ccxt.binance") as mock_cls:
            mock_cls.return_value = mock_exchange
            prov = CCXTProvider("binance")
        return prov

    def test_init_default_exchange(self) -> None:
        """测试默认使用 binance 交易所初始化。"""
        with patch("src.data.providers.ccxt_provider.ccxt.binance") as mock_cls:
            mock_exchange = MagicMock()
            mock_cls.return_value = mock_exchange
            prov = CCXTProvider()
            assert prov._exchange_id == "binance"
            mock_cls.assert_called_once()

    def test_init_unsupported_exchange(self) -> None:
        """测试不支持的交易所抛出 DataProviderError。"""
        with pytest.raises(DataProviderError, match="不支持的交易所"):
            CCXTProvider("nonexistent_exchange")

    def test_get_historical_data_success(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 fetch_ohlcv 成功返回数据。"""

        def _side_effect(symbol: str, timeframe: str, since: int) -> list[list[Any]]:
            if since <= 1_700_000_000_000:
                return [
                    [1_700_000_000_000, 100.0, 110.0, 90.0, 105.0, 1000.0],
                    [1_700_086_400_000, 105.0, 115.0, 95.0, 110.0, 1500.0],
                ]
            return []

        mock_exchange.fetch_ohlcv.side_effect = _side_effect

        request = MarketDataRequest(
            symbol="BTC/USDT",
            start_date=datetime(2023, 11, 14, 0, 0, tzinfo=timezone.utc),
            end_date=datetime(2023, 11, 16, 0, 0, tzinfo=timezone.utc),
            interval=DataInterval.DAY_1,
            asset_type=AssetType.CRYPTO,
        )

        result = provider.get_historical_data(request)

        assert len(result) == 2
        assert result[0].symbol == "BTC/USDT"
        assert result[0].open == 100.0
        assert result[0].high == 110.0
        assert result[0].low == 90.0
        assert result[0].close == 105.0
        assert result[0].volume == 1000.0
        assert result[1].close == 110.0
        assert mock_exchange.fetch_ohlcv.call_count == 2

    def test_get_historical_data_empty(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 fetch_ohlcv 返回空列表。"""
        mock_exchange.fetch_ohlcv.return_value = []

        request = MarketDataRequest(
            symbol="BTC/USDT",
            start_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
            end_date=datetime(2023, 11, 15, tzinfo=timezone.utc),
            interval=DataInterval.DAY_1,
            asset_type=AssetType.CRYPTO,
        )

        result = provider.get_historical_data(request)
        assert result == []

    def test_get_historical_data_unsupported_interval(
        self, provider: CCXTProvider
    ) -> None:
        """测试不支持的时间间隔抛出 DataProviderError。"""
        # 通过 monkeypatch 移除一个已映射的时间间隔来触发不支持的情况
        original_map = dict(provider._TIMEFRAME_MAP)
        provider._TIMEFRAME_MAP.clear()
        try:
            request = MarketDataRequest(
                symbol="BTC/USDT",
                start_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
                end_date=datetime(2023, 11, 15, tzinfo=timezone.utc),
                interval=DataInterval.DAY_1,
                asset_type=AssetType.CRYPTO,
            )
            with pytest.raises(DataProviderError, match="不支持的时间间隔"):
                provider.get_historical_data(request)
        finally:
            provider._TIMEFRAME_MAP.update(original_map)

    def test_get_historical_data_network_error(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 ccxt NetworkError 转换为 DataProviderError。"""
        import ccxt

        mock_exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("连接超时")

        request = MarketDataRequest(
            symbol="BTC/USDT",
            start_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
            end_date=datetime(2023, 11, 15, tzinfo=timezone.utc),
            interval=DataInterval.DAY_1,
            asset_type=AssetType.CRYPTO,
        )

        with pytest.raises(DataProviderError, match="网络错误"):
            provider.get_historical_data(request)

    def test_get_historical_data_exchange_error(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 ccxt ExchangeError 转换为 DataProviderError。"""
        import ccxt

        mock_exchange.fetch_ohlcv.side_effect = ccxt.ExchangeError("交易所维护中")

        request = MarketDataRequest(
            symbol="BTC/USDT",
            start_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
            end_date=datetime(2023, 11, 15, tzinfo=timezone.utc),
            interval=DataInterval.DAY_1,
            asset_type=AssetType.CRYPTO,
        )

        with pytest.raises(DataProviderError, match="交易所错误"):
            provider.get_historical_data(request)

    def test_get_historical_data_base_error(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 ccxt BaseError 转换为 DataProviderError。"""
        import ccxt

        mock_exchange.fetch_ohlcv.side_effect = ccxt.BaseError("未知错误")

        request = MarketDataRequest(
            symbol="BTC/USDT",
            start_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
            end_date=datetime(2023, 11, 15, tzinfo=timezone.utc),
            interval=DataInterval.DAY_1,
            asset_type=AssetType.CRYPTO,
        )

        with pytest.raises(DataProviderError, match="CCXT 错误"):
            provider.get_historical_data(request)

    def test_get_latest_price_success(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 fetch_ticker 成功返回最新价格。"""
        mock_exchange.fetch_ticker.return_value = {"last": 42000.0}

        price = provider.get_latest_price("BTC/USDT")
        assert price == 42000.0
        mock_exchange.fetch_ticker.assert_called_once_with("BTC/USDT")

    def test_get_latest_price_missing_last(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 ticker 中缺少 last 字段抛出 DataProviderError。"""
        mock_exchange.fetch_ticker.return_value = {}

        with pytest.raises(DataProviderError, match="无法获取 .* 的最新价格"):
            provider.get_latest_price("BTC/USDT")

    def test_get_latest_price_network_error(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 fetch_ticker NetworkError 转换为 DataProviderError。"""
        import ccxt

        mock_exchange.fetch_ticker.side_effect = ccxt.NetworkError("连接超时")

        with pytest.raises(DataProviderError, match="网络错误"):
            provider.get_latest_price("BTC/USDT")

    def test_get_latest_price_exchange_error(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 fetch_ticker ExchangeError 转换为 DataProviderError。"""
        import ccxt

        mock_exchange.fetch_ticker.side_effect = ccxt.ExchangeError("交易所维护中")

        with pytest.raises(DataProviderError, match="交易所错误"):
            provider.get_latest_price("BTC/USDT")

    def test_get_latest_price_base_error(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试 fetch_ticker BaseError 转换为 DataProviderError。"""
        import ccxt

        mock_exchange.fetch_ticker.side_effect = ccxt.BaseError("未知错误")

        with pytest.raises(DataProviderError, match="CCXT 错误"):
            provider.get_latest_price("BTC/USDT")

    def test_supports_crypto(self, provider: CCXTProvider) -> None:
        """测试 supports 对 CRYPTO 返回 True。"""
        assert provider.supports(AssetType.CRYPTO) is True

    def test_supports_stock(self, provider: CCXTProvider) -> None:
        """测试 supports 对 STOCK 返回 False。"""
        assert provider.supports(AssetType.STOCK) is False

    def test_supports_forex(self, provider: CCXTProvider) -> None:
        """测试 supports 对 FOREX 返回 False。"""
        assert provider.supports(AssetType.FOREX) is False

    def test_get_historical_data_pagination(
        self, provider: CCXTProvider, mock_exchange: MagicMock
    ) -> None:
        """测试分页拉取历史数据。"""
        call_count = 0

        def side_effect(symbol: str, timeframe: str, since: int) -> list[list[Any]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [
                    [1_700_000_000_000, 100.0, 110.0, 90.0, 105.0, 1000.0],
                ]
            return []

        mock_exchange.fetch_ohlcv.side_effect = side_effect

        request = MarketDataRequest(
            symbol="BTC/USDT",
            start_date=datetime(2023, 11, 14, tzinfo=timezone.utc),
            end_date=datetime(2023, 11, 20, tzinfo=timezone.utc),
            interval=DataInterval.DAY_1,
            asset_type=AssetType.CRYPTO,
        )

        result = provider.get_historical_data(request)
        assert len(result) == 1
        assert call_count == 2
