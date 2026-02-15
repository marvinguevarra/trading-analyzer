"""Tests for the auto-detect CSV parser."""

import pytest

from src.utils.csv_parser import auto_detect_csv


def _make_csv(content: str) -> bytes:
    return content.encode("utf-8")


class TestAutoDetectCSV:
    def test_standard_csv(self):
        csv = _make_csv(
            "date,open,high,low,close,volume\n"
            "2024-01-01,100,105,95,102,1000000\n"
            "2024-01-02,102,108,100,106,1200000\n"
            "2024-01-03,106,110,104,108,1100000\n"
        )
        df = auto_detect_csv(csv)
        assert len(df) == 3
        assert list(df.columns) == ["date", "close", "open", "high", "low", "volume"]
        assert df["close"].iloc[0] == 102

    def test_yahoo_finance_format(self):
        csv = _make_csv(
            "Date,Open,High,Low,Close,Adj Close,Volume\n"
            "2024-01-02,100.0,105.0,95.0,102.0,102.0,1000000\n"
            "2024-01-03,102.0,108.0,100.0,106.0,106.0,1200000\n"
        )
        df = auto_detect_csv(csv)
        assert "date" in df.columns
        assert "close" in df.columns
        assert len(df) == 2

    def test_tradingview_format(self):
        csv = _make_csv(
            "time,open,high,low,close,Volume\n"
            "2024-01-01,100,105,95,102,1000000\n"
            "2024-01-02,102,108,100,106,1200000\n"
        )
        df = auto_detect_csv(csv)
        assert "date" in df.columns
        assert "close" in df.columns

    def test_semicolon_delimiter(self):
        csv = _make_csv(
            "date;close;volume\n"
            "2024-01-01;102;1000000\n"
            "2024-01-02;106;1200000\n"
        )
        df = auto_detect_csv(csv)
        assert len(df) == 2
        assert "date" in df.columns
        assert "close" in df.columns

    def test_tab_delimiter(self):
        csv = _make_csv(
            "date\tclose\tvolume\n"
            "2024-01-01\t102\t1000000\n"
            "2024-01-02\t106\t1200000\n"
        )
        df = auto_detect_csv(csv)
        assert len(df) == 2

    def test_close_only_required(self):
        csv = _make_csv(
            "date,close\n"
            "2024-01-01,102\n"
            "2024-01-02,106\n"
        )
        df = auto_detect_csv(csv)
        assert len(df) == 2
        assert "open" not in df.columns

    def test_missing_date_raises(self):
        csv = _make_csv(
            "open,high,low,close,volume\n"
            "100,105,95,102,1000000\n"
        )
        with pytest.raises(ValueError, match="[Cc]ould not find date"):
            auto_detect_csv(csv)

    def test_missing_close_raises(self):
        csv = _make_csv(
            "date,open,high,low\n"
            "2024-01-01,100,105,95\n"
        )
        with pytest.raises(ValueError, match="[Mm]issing close"):
            auto_detect_csv(csv)

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            auto_detect_csv(b"")

    def test_empty_content_raises(self):
        with pytest.raises(ValueError, match="[Ee]mpty"):
            auto_detect_csv(b"   ")

    def test_no_data_rows_raises(self):
        csv = _make_csv("date,close\n")
        with pytest.raises(ValueError):
            auto_detect_csv(csv)

    def test_sorted_by_date(self):
        csv = _make_csv(
            "date,close\n"
            "2024-01-03,108\n"
            "2024-01-01,102\n"
            "2024-01-02,106\n"
        )
        df = auto_detect_csv(csv)
        assert df["date"].is_monotonic_increasing

    def test_drops_null_close(self):
        csv = _make_csv(
            "date,close\n"
            "2024-01-01,102\n"
            "2024-01-02,\n"
            "2024-01-03,108\n"
        )
        df = auto_detect_csv(csv)
        assert len(df) == 2

    def test_numeric_dtypes(self):
        csv = _make_csv(
            "date,open,high,low,close,volume\n"
            "2024-01-01,100,105,95,102,1000000\n"
            "2024-01-02,102,108,100,106,1200000\n"
        )
        df = auto_detect_csv(csv)
        assert df["close"].dtype in ("float64", "int64")
        assert df["volume"].dtype in ("float64", "int64")

    def test_datetime_column(self):
        csv = _make_csv(
            "datetime,close\n"
            "2024-01-01 09:30:00,102\n"
            "2024-01-01 09:31:00,103\n"
        )
        df = auto_detect_csv(csv)
        assert "date" in df.columns

    def test_timestamp_column(self):
        csv = _make_csv(
            "timestamp,close\n"
            "2024-01-01,102\n"
            "2024-01-02,106\n"
        )
        df = auto_detect_csv(csv)
        assert "date" in df.columns

    def test_last_price_column(self):
        csv = _make_csv(
            "date,last\n"
            "2024-01-01,102\n"
            "2024-01-02,106\n"
        )
        df = auto_detect_csv(csv)
        assert "close" in df.columns
        assert df["close"].iloc[0] == 102

    def test_price_column(self):
        csv = _make_csv(
            "date,price\n"
            "2024-01-01,102\n"
            "2024-01-02,106\n"
        )
        df = auto_detect_csv(csv)
        assert "close" in df.columns

    def test_vol_column(self):
        csv = _make_csv(
            "date,close,vol\n"
            "2024-01-01,102,5000\n"
            "2024-01-02,106,6000\n"
        )
        df = auto_detect_csv(csv)
        assert "volume" in df.columns
