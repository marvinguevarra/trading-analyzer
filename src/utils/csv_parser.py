"""Auto-detect CSV parser.

Parses CSV files from any platform (TradingView, Yahoo Finance, Think or Swim,
Interactive Brokers, etc.) by auto-detecting delimiter, date column, and price
columns. Returns a standardized pandas DataFrame.
"""

import io
from typing import Optional

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("csv_autodetect")

# Patterns for identifying columns (checked in order)
DATE_PATTERNS = ["date", "time", "datetime", "timestamp"]
CLOSE_PATTERNS = ["close", "last", "price"]
OPEN_PATTERNS = ["open"]
HIGH_PATTERNS = ["high"]
LOW_PATTERNS = ["low"]
VOLUME_PATTERNS = ["volume", "vol"]


def auto_detect_csv(file_content: bytes) -> pd.DataFrame:
    """Auto-detect and parse any CSV format without user input.

    Supports:
    - TradingView
    - Yahoo Finance
    - Think or Swim
    - Interactive Brokers
    - Most standard CSV formats

    Args:
        file_content: Raw CSV file bytes.

    Returns:
        DataFrame with standardized columns: date, close (required)
        plus open, high, low, volume (optional).

    Raises:
        ValueError: If date or close column not found, or file is unparseable.
    """
    if not file_content or not file_content.strip():
        raise ValueError("File is empty")

    # Parse CSV with auto-delimiter detection
    try:
        df = pd.read_csv(
            io.BytesIO(file_content),
            sep=None,
            engine="python",
        )
    except Exception as e:
        raise ValueError(f"Unable to parse CSV file: {e}")

    if df.empty:
        raise ValueError("CSV file contains no data rows")

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    logger.info(f"Detected columns: {list(df.columns)}")

    # Find and rename date column
    date_col = _find_column(df.columns, DATE_PATTERNS)
    if date_col is None:
        raise ValueError(
            "Could not find date column. Expected one of: "
            f"{', '.join(DATE_PATTERNS)}. "
            f"Found columns: {list(df.columns)}"
        )

    # Find and rename close column
    close_col = _find_column(df.columns, CLOSE_PATTERNS)
    if close_col is None:
        raise ValueError(
            "Missing close price data. Expected one of: "
            f"{', '.join(CLOSE_PATTERNS)}. "
            f"Found columns: {list(df.columns)}"
        )

    # Build rename mapping
    rename_map = {date_col: "date", close_col: "close"}

    # Optional columns
    open_col = _find_column(df.columns, OPEN_PATTERNS)
    if open_col:
        rename_map[open_col] = "open"

    high_col = _find_column(df.columns, HIGH_PATTERNS)
    if high_col:
        rename_map[high_col] = "high"

    low_col = _find_column(df.columns, LOW_PATTERNS)
    if low_col:
        rename_map[low_col] = "low"

    vol_col = _find_column(df.columns, VOLUME_PATTERNS)
    if vol_col:
        rename_map[vol_col] = "volume"

    df = df.rename(columns=rename_map)

    # Keep only recognized columns
    keep_cols = ["date", "close"]
    for col in ["open", "high", "low", "volume"]:
        if col in df.columns:
            keep_cols.append(col)
    df = df[keep_cols]

    # Parse dates
    try:
        df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True)
    except Exception:
        # Try unix timestamp
        try:
            df["date"] = pd.to_datetime(df["date"], unit="s")
        except Exception:
            raise ValueError(
                "Unable to parse dates. Ensure the date column contains "
                "recognizable date formats (e.g., 2024-01-15, 01/15/2024)."
            )

    # Convert price columns to numeric
    price_cols = [c for c in ["open", "high", "low", "close"] if c in df.columns]
    for col in price_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    # Drop rows with null close prices
    df = df.dropna(subset=["close"])

    if df.empty:
        raise ValueError("No valid price data found after parsing")

    # Sort by date, reset index
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        f"Parsed {len(df)} rows | "
        f"{df['date'].iloc[0].strftime('%Y-%m-%d')} to "
        f"{df['date'].iloc[-1].strftime('%Y-%m-%d')} | "
        f"Columns: {list(df.columns)}"
    )

    return df


def _find_column(
    columns: pd.Index, patterns: list[str]
) -> Optional[str]:
    """Find the first column matching any of the given patterns."""
    for col in columns:
        for pattern in patterns:
            if col == pattern or col.startswith(pattern):
                return col
    return None
