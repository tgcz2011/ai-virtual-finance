from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Log, Static


class TradingScreen(Screen[None]):
    """Trading screen showing order book, trades, and positions."""

    BINDINGS = [
        ("t", "noop", "Trading"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the trading layout."""
        yield Header(show_clock=True)
        with Container(id="trading-container"):
            with Horizontal(id="trading-top"):
                with Container(id="order-book-container"):
                    yield Static("Order Book", id="order-book-title")
                    yield DataTable(id="order-book-table")
                with Container(id="trades-container"):
                    yield Static("Recent Trades", id="trades-title")
                    yield DataTable(id="trades-table")
            with Container(id="positions-container"):
                yield Static("Positions", id="positions-title")
                yield DataTable(id="positions-table")
            yield Log(id="trading-log")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize widgets on mount."""
        order_book: DataTable[str] = self.query_one("#order-book-table", DataTable)
        order_book.add_columns("Side", "Price", "Size", "Total")
        order_book.add_rows([
            ("ASK", "150.50", "100", "15,050"),
            ("ASK", "150.25", "200", "30,050"),
            ("BID", "149.75", "150", "22,463"),
            ("BID", "149.50", "300", "44,850"),
        ])

        trades: DataTable[str] = self.query_one("#trades-table", DataTable)
        trades.add_columns("Time", "Symbol", "Side", "Price", "Size")
        trades.add_rows([
            ("10:00:01", "AAPL", "BUY", "150.00", "100"),
            ("10:00:15", "GOOGL", "SELL", "2800.00", "50"),
            ("10:01:02", "TSLA", "BUY", "700.00", "200"),
        ])

        positions: DataTable[str] = self.query_one("#positions-table", DataTable)
        positions.add_columns("Symbol", "Qty", "Avg Price", "Market Price", "P&L")
        positions.add_rows([
            ("AAPL", "100", "148.50", "150.00", "+150.00"),
            ("GOOGL", "-50", "2820.00", "2800.00", "+1000.00"),
            ("TSLA", "200", "695.00", "700.00", "+1000.00"),
        ])

        log: Log = self.query_one("#trading-log", Log)
        log.write_line("Trading session initialized.")
        log.write_line("Connected to market data feed.")

    def action_noop(self) -> None:
        """No-op action for trading binding."""
