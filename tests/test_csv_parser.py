"""Tests for the CSV Parser module."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.parsers.csv_parser import (
    DataQuality,
    ParsedData,
    _assess_quality,
    _detect_timeframe,
    _extract_symbol,
    _identify_indicators,
    _normalize_columns,
    load_csv,
)

# Path to sample data
SAMPLE_DIR = Path(__file__).parent.parent / "data" / "samples"
WHR_CSV = SAMPLE_DIR / "NYSE_WHR__1M.csv"


class TestLoadCSV:
    """Tests for the main load_csv function."""

    def test_load_whr_sample(self):
        """Load the WHR monthly sample data."""
        result = load_csv(str(WHR_CSV))
        assert isinstance(result, ParsedData)
        assert result.symbol == "WHR"
        assert result.bar_count == 26
        assert result.timeframe == "1M"
        assert result.quality.is_valid

    def test_load_returns_correct_columns(self):
        """Verify OHLCV columns are present and normalized."""
        result = load_csv(str(WHR_CSV))
        required = {"time", "open", "high", "low", "close", "volume"}
        assert required.issubset(set(result.df.columns))

    def test_load_detects_indicators(self):
        """Verify indicator columns are detected."""
        result = load_csv(str(WHR_CSV))
        assert len(result.indicators) > 0
        # WHR sample has RSI, MACD, BB, SMA columns
        indicator_names = [i.lower() for i in result.indicators]
        assert any("rsi" in name for name in indicator_names)
        assert any("macd" in name for name in indicator_names)
        assert any("sma" in name for name in indicator_names)

    def test_load_sorts_by_time(self):
        """Verify data is sorted by time ascending."""
        result = load_csv(str(WHR_CSV))
        times = result.df["time"].tolist()
        assert times == sorted(times)

    def test_load_date_range(self):
        """Verify date range is extracted."""
        result = load_csv(str(WHR_CSV))
        assert result.date_range[0] == "2023-01-01"
        assert result.date_range[1] == "2025-02-01"

    def test_load_file_not_found(self):
        """Raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_csv("/nonexistent/path/data.csv")

    def test_load_missing_columns(self):
        """Raise ValueError if required columns are missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("time,open,high\n2024-01-01,100,105\n")
            f.flush()
            try:
                with pytest.raises(ValueError, match="Missing required columns"):
                    load_csv(f.name)
            finally:
                os.unlink(f.name)


class TestNormalizeColumns:
    """Tests for column normalization."""

    def test_lowercase_standard_columns(self):
        df = pd.DataFrame({"Time": [1], "Open": [2], "High": [3], "Low": [4], "Close": [5]})
        result = _normalize_columns(df)
        assert set(result.columns) == {"time", "open", "high", "low", "close"}

    def test_volume_variations(self):
        """Handle various volume column names."""
        for vol_name in ["Volume", "VOLUME", "Vol", "vol", "v"]:
            df = pd.DataFrame({
                "time": [1], "open": [2], "high": [3], "low": [4], "close": [5],
                vol_name: [1000]
            })
            result = _normalize_columns(df)
            assert "volume" in result.columns

    def test_preserves_indicator_columns(self):
        """Indicator columns are kept with cleaned names."""
        df = pd.DataFrame({
            "time": [1], "open": [2], "high": [3], "low": [4], "close": [5],
            "RSI": [50], "MACD.macd": [1.5],
        })
        result = _normalize_columns(df)
        assert "rsi" in result.columns
        assert "macd.macd" in result.columns


class TestTimeframeDetection:
    """Tests for automatic timeframe detection."""

    def test_detect_monthly(self):
        dates = pd.date_range("2023-01-01", periods=12, freq="MS")
        df = pd.DataFrame({"time": dates, "close": range(12)})
        assert _detect_timeframe(df) == "1M"

    def test_detect_daily(self):
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        df = pd.DataFrame({"time": dates, "close": range(30)})
        assert _detect_timeframe(df) == "1d"

    def test_detect_weekly(self):
        dates = pd.date_range("2024-01-01", periods=20, freq="W")
        df = pd.DataFrame({"time": dates, "close": range(20)})
        assert _detect_timeframe(df) == "1w"

    def test_detect_hourly(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        df = pd.DataFrame({"time": dates, "close": range(100)})
        assert _detect_timeframe(df) == "1h"

    def test_single_row_returns_unknown(self):
        df = pd.DataFrame({"time": [pd.Timestamp("2024-01-01")], "close": [100]})
        assert _detect_timeframe(df) == "unknown"


class TestSymbolExtraction:
    """Tests for extracting symbol from filename."""

    def test_tradingview_format(self):
        assert _extract_symbol("NYSE_WHR__1M") == "WHR"

    def test_simple_format(self):
        assert _extract_symbol("AAPL_1D") == "AAPL"

    def test_crypto_exchange(self):
        assert _extract_symbol("BINANCE_BTCUSD") == "BTCUSD"

    def test_no_exchange(self):
        assert _extract_symbol("MSFT") == "MSFT"


class TestDataQuality:
    """Tests for data quality assessment."""

    def test_good_quality_data(self):
        """Clean data should score high."""
        result = load_csv(str(WHR_CSV))
        assert result.quality.score >= 0.8
        assert result.quality.is_valid
        assert len(result.quality.errors) == 0

    def test_missing_values_detected(self):
        """Missing values should reduce quality score."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=20, freq="D"),
            "open": [100] * 18 + [None, None],
            "high": [105] * 20,
            "low": [95] * 20,
            "close": [102] * 20,
        })
        quality = _assess_quality(df)
        assert quality.missing_values.get("open", 0) == 2
        assert quality.score < 1.0

    def test_ohlc_violation_detected(self):
        """OHLC violations should be flagged."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 101, 102, 103, 104],
            "high": [90, 106, 107, 108, 109],  # First bar: high < open (violation)
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
        })
        quality = _assess_quality(df)
        assert any("OHLC" in e for e in quality.errors)

    def test_too_few_rows(self):
        """Very few rows should reduce quality."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [102, 103, 104],
        })
        quality = _assess_quality(df)
        assert quality.score < 1.0
        assert any("few rows" in e.lower() for e in quality.errors)
