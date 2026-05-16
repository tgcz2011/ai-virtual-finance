from __future__ import annotations

import pytest

from src.engine.fee.calculator import (
    CryptoFeeCalculator,
    FeeBreakdown,
    USStockFeeCalculator,
)
from src.engine.portfolio.models import OrderSide, Trade


class TestUSStockFeeCalculator:
    def test_buy(self) -> None:
        calc = USStockFeeCalculator()
        trade = Trade(symbol="AAPL", quantity=500, price=150.0, side=OrderSide.BUY)
        fee = calc.calculate(trade)

        assert fee.commission == 500 * 0.005
        assert fee.slippage == 500 * 150.0 * 0.0001
        assert fee.tax == 0.0
        assert fee.total == fee.commission + fee.slippage + fee.tax

    def test_sell(self) -> None:
        calc = USStockFeeCalculator()
        trade = Trade(symbol="AAPL", quantity=500, price=150.0, side=OrderSide.SELL)
        fee = calc.calculate(trade)

        assert fee.commission == 500 * 0.005
        assert fee.slippage == 500 * 150.0 * 0.0001
        assert fee.tax == 500 * 150.0 * 0.30
        assert fee.total == fee.commission + fee.slippage + fee.tax

    def test_min_commission(self) -> None:
        calc = USStockFeeCalculator()
        trade = Trade(symbol="AAPL", quantity=10, price=150.0, side=OrderSide.BUY)
        fee = calc.calculate(trade)

        assert fee.commission == 1.0

    def test_fee_breakdown_immutable(self) -> None:
        fee = FeeBreakdown(commission=1.0, slippage=0.5, tax=0.0, total=1.5)
        with pytest.raises(Exception):
            fee.commission = 2.0


class TestCryptoFeeCalculator:
    def test_buy(self) -> None:
        calc = CryptoFeeCalculator()
        trade = Trade(symbol="BTC", quantity=1, price=50000.0, side=OrderSide.BUY)
        fee = calc.calculate(trade)

        assert fee.commission == 50000.0 * 0.001
        assert fee.slippage == 50000.0 * 0.0005
        assert fee.tax == 0.0
        assert fee.total == fee.commission + fee.slippage

    def test_sell(self) -> None:
        calc = CryptoFeeCalculator()
        trade = Trade(symbol="ETH", quantity=10, price=3000.0, side=OrderSide.SELL)
        fee = calc.calculate(trade)

        assert fee.commission == 10 * 3000.0 * 0.001
        assert fee.slippage == 10 * 3000.0 * 0.0005
        assert fee.tax == 0.0
        assert fee.total == fee.commission + fee.slippage

    def test_small_trade(self) -> None:
        calc = CryptoFeeCalculator()
        trade = Trade(symbol="BTC", quantity=100, price=500.0, side=OrderSide.BUY)
        fee = calc.calculate(trade)

        assert fee.commission == 100 * 500.0 * 0.001
        assert fee.slippage == 100 * 500.0 * 0.0005
        assert fee.total == fee.commission + fee.slippage
