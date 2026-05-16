from __future__ import annotations

from datetime import date

import pytest

from src.data.calendar.trading_calendar import CryptoCalendar, TradingCalendar, USStockCalendar


class TestUSStockCalendar:
    """USStockCalendar 单元测试。"""

    @pytest.fixture
    def calendar(self) -> USStockCalendar:
        """返回美股交易日历实例。"""
        return USStockCalendar()

    def test_weekday_is_trading_day(self, calendar: USStockCalendar) -> None:
        """测试普通工作日是交易日。"""
        assert calendar.is_trading_day(date(2024, 1, 2)) is True
        assert calendar.is_trading_day(date(2024, 6, 3)) is True

    def test_saturday_not_trading_day(self, calendar: USStockCalendar) -> None:
        """测试周六不是交易日。"""
        assert calendar.is_trading_day(date(2024, 1, 6)) is False

    def test_sunday_not_trading_day(self, calendar: USStockCalendar) -> None:
        """测试周日不是交易日。"""
        assert calendar.is_trading_day(date(2024, 1, 7)) is False

    def test_new_year_holiday(self, calendar: USStockCalendar) -> None:
        """测试元旦休市。"""
        assert calendar.is_trading_day(date(2024, 1, 1)) is False
        assert calendar.is_trading_day(date(2025, 1, 1)) is False

    def test_martin_luther_king_day(self, calendar: USStockCalendar) -> None:
        """测试马丁·路德·金纪念日休市。"""
        assert calendar.is_trading_day(date(2024, 1, 15)) is False
        assert calendar.is_trading_day(date(2025, 1, 20)) is False

    def test_presidents_day(self, calendar: USStockCalendar) -> None:
        """测试总统日休市。"""
        assert calendar.is_trading_day(date(2024, 2, 19)) is False
        assert calendar.is_trading_day(date(2025, 2, 17)) is False

    def test_good_friday(self, calendar: USStockCalendar) -> None:
        """测试耶稣受难日休市。"""
        assert calendar.is_trading_day(date(2024, 3, 29)) is False
        assert calendar.is_trading_day(date(2025, 4, 18)) is False

    def test_memorial_day(self, calendar: USStockCalendar) -> None:
        """测试阵亡将士纪念日休市。"""
        assert calendar.is_trading_day(date(2024, 5, 27)) is False
        assert calendar.is_trading_day(date(2025, 5, 26)) is False

    def test_juneteenth(self, calendar: USStockCalendar) -> None:
        """测试六月节休市。"""
        assert calendar.is_trading_day(date(2024, 6, 19)) is False
        assert calendar.is_trading_day(date(2025, 6, 19)) is False

    def test_independence_day(self, calendar: USStockCalendar) -> None:
        """测试独立日休市。"""
        assert calendar.is_trading_day(date(2024, 7, 4)) is False
        assert calendar.is_trading_day(date(2025, 7, 4)) is False

    def test_labor_day(self, calendar: USStockCalendar) -> None:
        """测试劳动节休市。"""
        assert calendar.is_trading_day(date(2024, 9, 2)) is False
        assert calendar.is_trading_day(date(2025, 9, 1)) is False

    def test_thanksgiving(self, calendar: USStockCalendar) -> None:
        """测试感恩节休市。"""
        assert calendar.is_trading_day(date(2024, 11, 28)) is False
        assert calendar.is_trading_day(date(2025, 11, 27)) is False

    def test_christmas_day(self, calendar: USStockCalendar) -> None:
        """测试圣诞节休市。"""
        assert calendar.is_trading_day(date(2024, 12, 25)) is False
        assert calendar.is_trading_day(date(2025, 12, 25)) is False

    def test_next_trading_day_from_weekday(self, calendar: USStockCalendar) -> None:
        """测试从工作日获取下一交易日。"""
        # 2024-01-02 is Tuesday, next is Wednesday
        assert calendar.next_trading_day(date(2024, 1, 2)) == date(2024, 1, 3)

    def test_next_trading_day_from_friday(self, calendar: USStockCalendar) -> None:
        """测试从周五获取下一交易日（跳过周末）。"""
        # 2024-01-05 is Friday, next is Monday 2024-01-08
        assert calendar.next_trading_day(date(2024, 1, 5)) == date(2024, 1, 8)

    def test_next_trading_day_skips_holiday(self, calendar: USStockCalendar) -> None:
        """测试下一交易日跳过节假日。"""
        # 2023-12-29 is Friday, next should skip weekend and New Year -> 2024-01-02
        assert calendar.next_trading_day(date(2023, 12, 29)) == date(2024, 1, 2)

    def test_previous_trading_day_from_weekday(self, calendar: USStockCalendar) -> None:
        """测试从工作日获取上一交易日。"""
        assert calendar.previous_trading_day(date(2024, 1, 3)) == date(2024, 1, 2)

    def test_previous_trading_day_from_monday(self, calendar: USStockCalendar) -> None:
        """测试从周一获取上一交易日（跳过周末）。"""
        # 2024-01-08 is Monday, previous is Friday 2024-01-05
        assert calendar.previous_trading_day(date(2024, 1, 8)) == date(2024, 1, 5)

    def test_previous_trading_day_skips_holiday(self, calendar: USStockCalendar) -> None:
        """测试上一交易日跳过节假日。"""
        # 2024-01-02 is Tuesday, previous should skip New Year -> 2023-12-29
        assert calendar.previous_trading_day(date(2024, 1, 2)) == date(2023, 12, 29)

    def test_trading_days_between_normal_week(self, calendar: USStockCalendar) -> None:
        """测试普通一周内的交易日列表。"""
        # 2024-01-08 (Mon) to 2024-01-12 (Fri)
        days = calendar.trading_days_between(date(2024, 1, 8), date(2024, 1, 12))
        expected = [
            date(2024, 1, 8),
            date(2024, 1, 9),
            date(2024, 1, 10),
            date(2024, 1, 11),
            date(2024, 1, 12),
        ]
        assert days == expected

    def test_trading_days_between_with_weekend(self, calendar: USStockCalendar) -> None:
        """测试跨周末的交易日列表。"""
        # 2024-01-05 (Fri) to 2024-01-08 (Mon)
        days = calendar.trading_days_between(date(2024, 1, 5), date(2024, 1, 8))
        expected = [date(2024, 1, 5), date(2024, 1, 8)]
        assert days == expected

    def test_trading_days_between_with_holiday(self, calendar: USStockCalendar) -> None:
        """测试跨节假日的交易日列表。"""
        # 2023-12-28 (Thu) to 2024-01-03 (Wed), skip weekend and New Year
        days = calendar.trading_days_between(date(2023, 12, 28), date(2024, 1, 3))
        expected = [
            date(2023, 12, 28),
            date(2023, 12, 29),
            date(2024, 1, 2),
            date(2024, 1, 3),
        ]
        assert days == expected

    def test_trading_days_between_start_after_end(self, calendar: USStockCalendar) -> None:
        """测试 start > end 时返回空列表。"""
        assert calendar.trading_days_between(date(2024, 1, 10), date(2024, 1, 5)) == []

    def test_trading_days_between_same_day(self, calendar: USStockCalendar) -> None:
        """测试 start == end 且为交易日。"""
        assert calendar.trading_days_between(date(2024, 1, 2), date(2024, 1, 2)) == [date(2024, 1, 2)]

    def test_trading_days_between_same_day_holiday(self, calendar: USStockCalendar) -> None:
        """测试 start == end 且为节假日。"""
        assert calendar.trading_days_between(date(2024, 1, 1), date(2024, 1, 1)) == []


class TestCryptoCalendar:
    """CryptoCalendar 单元测试。"""

    @pytest.fixture
    def calendar(self) -> CryptoCalendar:
        """返回加密货币交易日历实例。"""
        return CryptoCalendar()

    def test_any_day_is_trading_day(self, calendar: CryptoCalendar) -> None:
        """测试任意日期都是交易日。"""
        assert calendar.is_trading_day(date(2024, 1, 1)) is True
        assert calendar.is_trading_day(date(2024, 1, 6)) is True  # Saturday
        assert calendar.is_trading_day(date(2024, 12, 25)) is True  # Christmas

    def test_next_trading_day_is_next_day(self, calendar: CryptoCalendar) -> None:
        """测试下一交易日就是明天。"""
        assert calendar.next_trading_day(date(2024, 1, 1)) == date(2024, 1, 2)
        assert calendar.next_trading_day(date(2024, 1, 6)) == date(2024, 1, 7)

    def test_previous_trading_day_is_yesterday(self, calendar: CryptoCalendar) -> None:
        """测试上一交易日就是昨天。"""
        assert calendar.previous_trading_day(date(2024, 1, 2)) == date(2024, 1, 1)
        assert calendar.previous_trading_day(date(2024, 1, 7)) == date(2024, 1, 6)

    def test_trading_days_between_all_days(self, calendar: CryptoCalendar) -> None:
        """测试区间内所有日期都是交易日。"""
        days = calendar.trading_days_between(date(2024, 1, 1), date(2024, 1, 5))
        expected = [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
        ]
        assert days == expected

    def test_trading_days_between_start_after_end(self, calendar: CryptoCalendar) -> None:
        """测试 start > end 时返回空列表。"""
        assert calendar.trading_days_between(date(2024, 1, 10), date(2024, 1, 5)) == []


class TestTradingCalendarAbstract:
    """TradingCalendar 抽象基类行为测试。"""

    def test_cannot_instantiate_directly(self) -> None:
        """测试不能直接实例化抽象基类。"""
        with pytest.raises(TypeError):
            TradingCalendar()  # type: ignore[abstract]
