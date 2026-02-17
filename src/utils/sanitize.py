"""Input sanitization for CSV data and user-provided strings.

Prevents prompt injection by ensuring only clean numeric data and
known column names reach the AI agents.
"""

import re

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("sanitize")

# Allowlist patterns for column names (matched after lowercase normalization).
# Columns not matching any pattern get renamed to "extra_col_N".
ALLOWED_COLUMN_PATTERNS = [
    re.compile(r"^(time|date|datetime|timestamp)$"),
    re.compile(r"^(open|high|low|close|volume|vol|adj.?close)$"),
    re.compile(r"^(rsi|macd|sma|ema|vwap|atr|adx|cci|obv|mfi)"),
    re.compile(r"^(bb|bollinger)"),
    re.compile(r"^(stoch|williams|ichimoku|keltner|donchian)"),
    re.compile(r"^(pivot|fib|psar|supertrend)"),
]


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize a DataFrame to prevent prompt injection.

    1. Renames unknown columns to extra_col_N.
    2. Coerces non-date columns to numeric (text becomes NaN).
    3. Drops columns that are >90% NaN after coercion.
    4. Logs security warnings for suspicious content.

    Args:
        df: Raw DataFrame after column normalization.

    Returns:
        Sanitized DataFrame safe for use in prompts.
    """
    df = df.copy()
    df = _sanitize_column_names(df)
    df = _sanitize_cell_values(df)
    return df


def sanitize_ticker(s: str) -> str:
    """Sanitize a ticker string: letters and dots only, max 10 chars.

    Args:
        s: Raw ticker string from user input or filename.

    Returns:
        Cleaned ticker string, uppercased.
    """
    cleaned = re.sub(r"[^A-Za-z.]", "", s)
    return cleaned.upper()[:10]


def _sanitize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns that don't match known OHLCV/indicator patterns."""
    rename_map = {}
    extra_idx = 0

    for col in df.columns:
        matched = any(p.match(col) for p in ALLOWED_COLUMN_PATTERNS)
        if not matched:
            extra_idx += 1
            safe_name = f"extra_col_{extra_idx}"
            rename_map[col] = safe_name
            logger.warning(
                f"Column '{col[:50]}' does not match known patterns, "
                f"renamed to '{safe_name}'"
            )

    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def _sanitize_cell_values(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce non-date columns to numeric; drop columns that are mostly NaN."""
    date_cols = {"time", "date", "datetime", "timestamp"}
    numeric_candidates = [c for c in df.columns if c not in date_cols]

    for col in numeric_candidates:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue

        # Check for suspiciously long strings before coercion
        str_lens = df[col].astype(str).apply(len)
        long_count = int((str_lens > 20).sum())
        if long_count > 0:
            logger.warning(
                f"SECURITY: column '{col}' has {long_count} cells with "
                f"strings >20 chars — coercing to NaN"
            )

        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop columns that are >90% NaN after coercion
    for col in list(df.columns):
        if col in date_cols:
            continue
        nan_pct = df[col].isna().sum() / max(len(df), 1)
        if nan_pct > 0.9:
            logger.warning(
                f"Dropping column '{col}': {nan_pct:.0%} NaN after coercion"
            )
            df = df.drop(columns=[col])

    return df
