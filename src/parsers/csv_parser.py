"""TradingView CSV Parser.

Parses TradingView-exported CSV files containing OHLCV data and optional
pre-calculated indicators (RSI, MACD, Bollinger Bands, SMAs).

Component 1 per PRD.md specification.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("csv_parser")

# Required columns (case-insensitive matching)
REQUIRED_COLUMNS = {"time", "open", "high", "low", "close"}

# Known indicator column patterns
INDICATOR_PATTERNS = {
    "rsi": re.compile(r"^rsi", re.IGNORECASE),
    "macd": re.compile(r"^macd", re.IGNORECASE),
    "bb_upper": re.compile(r"^bb\.?upper|^bollinger.*upper", re.IGNORECASE),
    "bb_lower": re.compile(r"^bb\.?lower|^bollinger.*lower", re.IGNORECASE),
    "sma": re.compile(r"^sma", re.IGNORECASE),
    "ema": re.compile(r"^ema", re.IGNORECASE),
    "volume": re.compile(r"^volume$", re.IGNORECASE),
}

# Timeframe detection thresholds (in seconds)
TIMEFRAME_THRESHOLDS = {
    "1m": 90,         # ~1 minute, with tolerance
    "5m": 400,        # ~5 minutes
    "15m": 1200,      # ~15 minutes
    "1h": 5400,       # ~1 hour
    "4h": 18000,      # ~4 hours
    "1d": 108000,     # ~1 day
    "1w": 700000,     # ~1 week
    "1M": 2800000,    # ~1 month
}


@dataclass
class DataQuality:
    """Data quality assessment results."""

    score: float  # 0.0 - 1.0
    total_rows: int
    missing_values: dict[str, int]
    gaps_detected: int
    duplicate_rows: int
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return self.score >= 0.5 and len(self.errors) == 0


@dataclass
class ParsedData:
    """Result of parsing a CSV file."""

    df: pd.DataFrame
    symbol: str
    timeframe: str
    date_range: tuple[str, str]
    quality: DataQuality
    indicators: list[str]

    @property
    def has_volume(self) -> bool:
        return "volume" in self.df.columns

    @property
    def bar_count(self) -> int:
        return len(self.df)


def load_csv(file_path: str, asset_class: str = "equities") -> ParsedData:
    """Load and parse a TradingView CSV file.

    Args:
        file_path: Path to the CSV file.
        asset_class: Asset class for context (equities, crypto, etc.)

    Returns:
        ParsedData with normalized DataFrame and metadata.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If required columns are missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    logger.info(f"Loading CSV: {file_path}")
    df = pd.read_csv(path)
    return _parse_dataframe(df, path.stem)


def parse_csv_content(content: bytes, filename: str = "upload.csv") -> ParsedData:
    """Parse CSV content from in-memory bytes.

    Behaves identically to load_csv but reads from bytes instead of
    a file path. Useful for uploaded files.

    Args:
        content: Raw CSV bytes.
        filename: Original filename (used for symbol extraction).

    Returns:
        ParsedData with normalized DataFrame and metadata.

    Raises:
        ValueError: If required columns are missing or data is invalid.
    """
    import io

    logger.info(f"Parsing CSV content: {filename} ({len(content):,} bytes)")
    df = pd.read_csv(io.BytesIO(content))
    return _parse_dataframe(df, Path(filename).stem)


def _parse_dataframe(df: pd.DataFrame, filename_stem: str) -> ParsedData:
    """Normalize, validate, and wrap a raw DataFrame into ParsedData.

    Shared implementation used by both load_csv and parse_csv_content.
    """
    logger.info(f"Raw data: {len(df)} rows, {len(df.columns)} columns")

    # Normalize columns
    df = _normalize_columns(df)

    # Validate required columns
    _validate_required_columns(df)

    # Parse datetime
    df = _parse_datetime(df)

    # Sort by time
    df = df.sort_values("time").reset_index(drop=True)

    # Extract metadata from filename
    symbol = _extract_symbol(filename_stem)

    # Detect timeframe
    timeframe = _detect_timeframe(df)

    # Identify indicators present
    indicators = _identify_indicators(df)

    # Run quality checks
    quality = _assess_quality(df)

    # Date range
    date_range = (
        df["time"].iloc[0].strftime("%Y-%m-%d"),
        df["time"].iloc[-1].strftime("%Y-%m-%d"),
    )

    logger.info(
        f"Parsed: {symbol} | {timeframe} | {date_range[0]} to {date_range[1]} | "
        f"{len(df)} bars | Quality: {quality.score:.0%} | "
        f"Indicators: {indicators}"
    )

    return ParsedData(
        df=df,
        symbol=symbol,
        timeframe=timeframe,
        date_range=date_range,
        quality=quality,
        indicators=indicators,
    )


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase standard format."""
    rename_map = {}
    for col in df.columns:
        lower = col.strip().lower()
        # Handle TradingView-specific naming
        if lower in ("time", "date", "datetime", "timestamp"):
            rename_map[col] = "time"
        elif lower in ("open", "o"):
            rename_map[col] = "open"
        elif lower in ("high", "h"):
            rename_map[col] = "high"
        elif lower in ("low", "l"):
            rename_map[col] = "low"
        elif lower in ("close", "c", "adj close"):
            rename_map[col] = "close"
        elif lower in ("volume", "vol", "v"):
            rename_map[col] = "volume"
        else:
            # Keep indicator columns with cleaned names
            cleaned = lower.replace(" ", "_")
            rename_map[col] = cleaned

    df = df.rename(columns=rename_map)
    return df


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Check that all required OHLC columns are present."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def _parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the time column into datetime."""
    df = df.copy()
    if df["time"].dtype in ("int64", "int32"):
        df["time"] = pd.to_datetime(df["time"], unit="s")
    else:
        df["time"] = pd.to_datetime(df["time"])
    return df


def _detect_timeframe(df: pd.DataFrame) -> str:
    """Auto-detect the data timeframe from timestamp intervals.

    Calculates the median interval between consecutive bars and matches
    to the closest known timeframe.
    """
    if len(df) < 2:
        return "unknown"

    # Calculate intervals in seconds
    intervals = df["time"].diff().dropna().dt.total_seconds()
    median_interval = intervals.median()

    # Match to closest timeframe
    best_match = "unknown"
    best_diff = float("inf")

    for tf, threshold in TIMEFRAME_THRESHOLDS.items():
        diff = abs(median_interval - threshold)
        if diff < best_diff:
            best_diff = diff
            best_match = tf

    logger.debug(
        f"Timeframe detection: median interval = {median_interval:.0f}s -> {best_match}"
    )
    return best_match


def _extract_symbol(filename: str) -> str:
    """Extract trading symbol from filename.

    TradingView format: NYSE_WHR__1M or BTCUSD_1D
    """
    # Remove exchange prefix if present (NYSE_, NASDAQ_, etc.)
    parts = filename.split("_")

    # Common exchange prefixes
    exchanges = {"NYSE", "NASDAQ", "AMEX", "LSE", "TSE", "BINANCE", "COINBASE", "CME"}

    if parts[0].upper() in exchanges and len(parts) > 1:
        # Skip exchange prefix, take symbol
        symbol = parts[1]
    else:
        symbol = parts[0]

    # Clean up: remove trailing timeframe indicators
    symbol = re.sub(r"__?\d+[mMhHdDwW]$", "", symbol)

    return symbol.upper()


def _identify_indicators(df: pd.DataFrame) -> list[str]:
    """Identify which pre-calculated indicators are present in the data."""
    found = []
    ohlcv = {"time", "open", "high", "low", "close", "volume"}

    for col in df.columns:
        if col in ohlcv:
            continue
        for indicator_name, pattern in INDICATOR_PATTERNS.items():
            if pattern.match(col):
                found.append(col)
                break
        else:
            # Column doesn't match known patterns but is still an indicator
            if col not in ohlcv:
                found.append(col)

    return found


def _assess_quality(df: pd.DataFrame) -> DataQuality:
    """Assess data quality and return a quality report."""
    errors = []
    warnings = []
    score = 1.0

    # Check total rows
    total_rows = len(df)
    if total_rows < 10:
        errors.append(f"Too few rows: {total_rows} (minimum 10)")
        score -= 0.3

    # Missing values in OHLC columns
    missing_values = {}
    for col in ["open", "high", "low", "close"]:
        missing = int(df[col].isna().sum())
        if missing > 0:
            missing_values[col] = missing
            pct = missing / total_rows
            if pct > 0.1:
                errors.append(f"{col}: {missing} missing values ({pct:.1%})")
                score -= 0.2
            else:
                warnings.append(f"{col}: {missing} missing values ({pct:.1%})")
                score -= 0.05

    if "volume" in df.columns:
        vol_missing = int(df["volume"].isna().sum())
        if vol_missing > 0:
            missing_values["volume"] = vol_missing
            warnings.append(f"volume: {vol_missing} missing values")
            score -= 0.02

    # Check for duplicates
    duplicate_rows = int(df["time"].duplicated().sum())
    if duplicate_rows > 0:
        warnings.append(f"{duplicate_rows} duplicate timestamps")
        score -= 0.05

    # Check for time gaps (missing bars)
    gaps = 0
    if len(df) > 2:
        intervals = df["time"].diff().dropna()
        median_interval = intervals.median()
        # A gap is when interval > 2x the median
        gap_threshold = median_interval * 2.5
        gaps = int((intervals > gap_threshold).sum())
        if gaps > 0:
            gap_pct = gaps / total_rows
            if gap_pct > 0.1:
                warnings.append(f"{gaps} time gaps detected ({gap_pct:.1%} of bars)")
                score -= 0.1
            else:
                warnings.append(f"{gaps} time gaps detected")

    # Check OHLC consistency (high >= low, high >= open/close, low <= open/close)
    ohlc_errors = 0
    if total_rows > 0:
        ohlc_errors += int((df["high"] < df["low"]).sum())
        ohlc_errors += int((df["high"] < df["open"]).sum())
        ohlc_errors += int((df["high"] < df["close"]).sum())
        ohlc_errors += int((df["low"] > df["open"]).sum())
        ohlc_errors += int((df["low"] > df["close"]).sum())
    if ohlc_errors > 0:
        errors.append(f"{ohlc_errors} OHLC consistency violations")
        score -= 0.15

    # Check for zero or negative prices
    for col in ["open", "high", "low", "close"]:
        bad = int((df[col] <= 0).sum())
        if bad > 0:
            errors.append(f"{col}: {bad} zero or negative values")
            score -= 0.1

    score = max(0.0, min(1.0, score))

    return DataQuality(
        score=score,
        total_rows=total_rows,
        missing_values=missing_values,
        gaps_detected=gaps,
        duplicate_rows=duplicate_rows,
        errors=errors,
        warnings=warnings,
    )
