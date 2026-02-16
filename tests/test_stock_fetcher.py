"""Tests for the yfinance stock data fetcher."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.utils.stock_fetcher import VALID_INTERVALS, VALID_PERIODS, fetch_stock_data


def _make_yf_df(rows: int = 20) -> pd.DataFrame:
    """Create a fake yfinance-style DataFrame with DatetimeIndex named 'Date'."""
    dates = pd.date_range("2024-01-01", periods=rows, freq="D", tz="America/New_York")
    dates.name = "Date"
    return pd.DataFrame(
        {
            "Open": range(100, 100 + rows),
            "High": range(105, 105 + rows),
            "Low": range(95, 95 + rows),
            "Close": range(102, 102 + rows),
            "Volume": [1_000_000] * rows,
            "Dividends": [0.0] * rows,
            "Stock Splits": [0.0] * rows,
        },
        index=dates,
    )


class TestFetchStockData:
    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_returns_dataframe(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        df = fetch_stock_data("AAPL", "1mo")

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 20

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_standard_columns(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        df = fetch_stock_data("AAPL")
        assert "date" in df.columns
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        # Extra columns should be stripped
        assert "Dividends" not in df.columns
        assert "Stock Splits" not in df.columns

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_ticker_uppercased(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        fetch_stock_data("aapl")
        mock_ticker_cls.assert_called_with("AAPL")

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_ticker_trimmed(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        fetch_stock_data("  AAPL  ")
        mock_ticker_cls.assert_called_with("AAPL")

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_empty_data_returns_none(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_ticker

        result = fetch_stock_data("INVALID")
        assert result is None

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_exception_returns_none(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = Exception("network error")

        result = fetch_stock_data("AAPL")
        assert result is None

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_timezone_stripped(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        df = fetch_stock_data("AAPL")
        assert df["date"].dt.tz is None

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_sorted_by_date(self, mock_ticker_cls):
        yf_df = _make_yf_df()
        # Reverse the order
        yf_df = yf_df.iloc[::-1]
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = yf_df
        mock_ticker_cls.return_value = mock_ticker

        df = fetch_stock_data("AAPL")
        assert df["date"].is_monotonic_increasing

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_invalid_period_defaults(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        fetch_stock_data("AAPL", period="invalid")
        mock_ticker.history.assert_called_with(period="1mo", interval="1d")

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_invalid_interval_defaults(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        fetch_stock_data("AAPL", interval="invalid")
        mock_ticker.history.assert_called_with(period="1mo", interval="1d")

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_interval_passed_to_yfinance(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        fetch_stock_data("AAPL", period="3mo", interval="1h")
        mock_ticker.history.assert_called_with(period="3mo", interval="1h")

    def test_valid_periods_constant(self):
        assert "1mo" in VALID_PERIODS
        assert "1y" in VALID_PERIODS
        assert "max" in VALID_PERIODS

    def test_valid_intervals_constant(self):
        assert "1d" in VALID_INTERVALS
        assert "1h" in VALID_INTERVALS
        assert "1wk" in VALID_INTERVALS

    @patch("src.utils.stock_fetcher.yf.Ticker")
    def test_numeric_dtypes(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()
        mock_ticker_cls.return_value = mock_ticker

        df = fetch_stock_data("AAPL")
        for col in ["open", "high", "low", "close", "volume"]:
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} should be numeric"
