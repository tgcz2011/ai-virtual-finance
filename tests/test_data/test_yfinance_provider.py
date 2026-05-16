from __future__ import annotations

import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from src.data.models import AssetType, DataInterval, MarketData
from src.data.providers.yfinance_provider import DataProviderError, YFinanceProvider


class TestYFinanceProvider(unittest.TestCase):
    """YFinanceProvider 单元测试。

    使用 unittest.mock 模拟 yfinance.Ticker，避免实际网络请求。
    """

    def setUp(self) -> None:
        """在每个测试方法前初始化 Provider 实例。"""
        self.provider = YFinanceProvider(min_request_interval=0.0)

    def _build_mock_history(self) -> pd.DataFrame:
        """构建模拟的历史数据 DataFrame。"""
        data = {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Volume": [1000000.0, 2000000.0],
        }
        index = pd.to_datetime(["2024-01-01", "2024-01-02"])
        return pd.DataFrame(data, index=index)

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_historical_data_success(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_historical_data 正常返回数据。"""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = self._build_mock_history()
        mock_ticker_cls.return_value = mock_ticker

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 3)
        result = self.provider.get_historical_data(
            symbol="AAPL",
            start_date=start,
            end_date=end,
            interval=DataInterval.DAY_1,
        )

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], MarketData)
        self.assertEqual(result[0].symbol, "AAPL")
        self.assertEqual(result[0].open, 100.0)
        self.assertEqual(result[0].high, 102.0)
        self.assertEqual(result[0].low, 99.0)
        self.assertEqual(result[0].close, 101.0)
        self.assertEqual(result[0].volume, 1000000.0)
        self.assertEqual(result[1].close, 102.0)

        mock_ticker.history.assert_called_once_with(
            start=start,
            end=end,
            interval="1d",
        )

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_historical_data_empty_raises(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_historical_data 返回空数据时抛出 DataProviderError。"""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_ticker

        with self.assertRaises(DataProviderError) as ctx:
            self.provider.get_historical_data(
                symbol="INVALID",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 3),
                interval=DataInterval.DAY_1,
            )

        self.assertIn("No historical data", str(ctx.exception))

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_historical_data_fetch_exception(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_historical_data 获取异常时抛出 DataProviderError。"""
        mock_ticker_cls.side_effect = RuntimeError("Network error")

        with self.assertRaises(DataProviderError) as ctx:
            self.provider.get_historical_data(
                symbol="AAPL",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 3),
                interval=DataInterval.DAY_1,
            )

        self.assertIn("Failed to fetch", str(ctx.exception))

    def test_get_historical_data_unsupported_interval(self) -> None:
        """测试不支持的 interval 抛出 DataProviderError。"""
        # 构造一个不在 _INTERVAL_MAP 中的 interval
        unsupported_interval = MagicMock(spec=DataInterval)
        unsupported_interval.value = "3d"
        # 由于 MagicMock 不是同一个枚举成员，not in dict 会返回 True
        with self.assertRaises(DataProviderError) as ctx:
            self.provider.get_historical_data(
                symbol="AAPL",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 3),
                interval=unsupported_interval,  # type: ignore[arg-type]
            )
        self.assertIn("Unsupported interval", str(ctx.exception))

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_latest_price_from_info(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_latest_price 从 info 获取价格。"""
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 150.5}
        mock_ticker_cls.return_value = mock_ticker

        price = self.provider.get_latest_price("AAPL")
        self.assertEqual(price, 150.5)

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_latest_price_from_history_fallback(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_latest_price 在 info 不可用时回退到 history。"""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker.history.return_value = self._build_mock_history()
        mock_ticker_cls.return_value = mock_ticker

        price = self.provider.get_latest_price("AAPL")
        self.assertEqual(price, 102.0)

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_latest_price_no_data_raises(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_latest_price 无数据时抛出 DataProviderError。"""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_ticker

        with self.assertRaises(DataProviderError) as ctx:
            self.provider.get_latest_price("UNKNOWN")

        self.assertIn("No price data available", str(ctx.exception))

    @patch("src.data.providers.yfinance_provider.yfinance.Ticker")
    def test_get_latest_price_exception(self, mock_ticker_cls: MagicMock) -> None:
        """测试 get_latest_price 异常时抛出 DataProviderError。"""
        mock_ticker_cls.side_effect = ConnectionError("Timeout")

        with self.assertRaises(DataProviderError) as ctx:
            self.provider.get_latest_price("AAPL")

        self.assertIn("Failed to fetch latest price", str(ctx.exception))

    def test_get_symbols_returns_empty_list(self) -> None:
        """测试 get_symbols 返回空列表。"""
        symbols = self.provider.get_symbols()
        self.assertEqual(symbols, [])

    def test_supports_stock(self) -> None:
        """测试 supports 对 STOCK 返回 True。"""
        self.assertTrue(self.provider.supports(AssetType.STOCK))

    def test_supports_not_stock(self) -> None:
        """测试 supports 对非 STOCK 返回 False。"""
        self.assertFalse(self.provider.supports(AssetType.CRYPTO))
        self.assertFalse(self.provider.supports(AssetType.FOREX))

    def test_get_intervals(self) -> None:
        """测试 get_intervals 返回支持的时间间隔。"""
        intervals = self.provider.get_intervals()
        self.assertIn(DataInterval.DAY_1, intervals)
        self.assertIn(DataInterval.HOUR_1, intervals)
        self.assertIn(DataInterval.MIN_1, intervals)

    def test_rate_limit_enforced(self) -> None:
        """测试请求频率限制生效。"""
        provider = YFinanceProvider(min_request_interval=0.1)
        # 第一次请求后 _last_request_time 被设置
        with patch.object(provider, "_create_ticker") as mock_create:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = self._build_mock_history()
            mock_create.return_value = mock_ticker

            provider.get_historical_data(
                symbol="AAPL",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 3),
                interval=DataInterval.DAY_1,
            )

            # 立即第二次请求应该触发 rate limit
            with patch("time.sleep") as mock_sleep:
                provider.get_historical_data(
                    symbol="AAPL",
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 1, 3),
                    interval=DataInterval.DAY_1,
                )
                mock_sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
