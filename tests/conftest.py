import os
import tempfile
from datetime import datetime, timedelta

import pandas as pd
import pytest


@pytest.fixture
def mock_market_data():
    """Return mock OHLCV market data as a pandas DataFrame."""
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    data = {
        "open": [100.0, 101.0, 102.0, 101.5, 103.0, 104.0, 103.5, 105.0, 106.0, 107.0],
        "high": [101.0, 102.0, 103.0, 102.5, 104.0, 105.0, 104.5, 106.0, 107.0, 108.0],
        "low": [99.0, 100.0, 101.0, 100.5, 102.0, 103.0, 102.5, 104.0, 105.0, 106.0],
        "close": [101.0, 102.0, 101.5, 103.0, 104.0, 103.5, 105.0, 106.0, 107.0, 108.0],
        "volume": [1000, 1100, 1050, 1200, 1150, 1300, 1250, 1400, 1350, 1500],
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = "timestamp"
    return df


@pytest.fixture
def mock_agent_config():
    """Return a mock agent configuration dictionary."""
    return {
        "agent_id": "test-agent-001",
        "name": "TestAgent",
        "strategy": "mock_strategy",
        "parameters": {
            "risk_tolerance": 0.05,
            "max_position_size": 100,
            "lookback_window": 20,
        },
        "enabled": True,
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def temp_db():
    """Return a temporary database file path."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_db_")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)
