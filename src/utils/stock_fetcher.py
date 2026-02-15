"""Stock data fetcher using yfinance.

Fetches historical OHLCV data for a given ticker and returns a standardized
DataFrame matching the format from auto_detect_csv.
"""

from typing import Optional

import pandas as pd
import yfinance as yf

from src.utils.logger import get_logger

logger = get_logger("stock_fetcher")

VALID_PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]


def fetch_stock_data(
    ticker: str, period: str = "1mo"
) -> Optional[pd.DataFrame]:
    """Fetch historical stock data using yfinance.

    Args:
        ticker: Stock symbol (e.g., "AAPL", "MSFT").
        period: Time period — valid values:
                1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

    Returns:
        DataFrame with columns: date, open, high, low, close, volume.
        Or None if ticker is invalid or no data is available.
    """
    ticker = ticker.strip().upper()

    if period not in VALID_PERIODS:
        logger.warning(f"Invalid period '{period}', defaulting to '1mo'")
        period = "1mo"

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if df.empty:
            logger.warning(f"No data returned for {ticker} (period={period})")
            return None

        # Normalize: reset index to get Date as column
        df = df.reset_index()

        # Rename columns to lowercase standard
        rename_map = {}
        for col in df.columns:
            lower = col.strip().lower()
            if lower in ("date", "datetime"):
                rename_map[col] = "date"
            elif lower == "open":
                rename_map[col] = "open"
            elif lower == "high":
                rename_map[col] = "high"
            elif lower == "low":
                rename_map[col] = "low"
            elif lower == "close":
                rename_map[col] = "close"
            elif lower in ("volume", "vol"):
                rename_map[col] = "volume"

        df = df.rename(columns=rename_map)

        # Keep only standard columns
        keep_cols = []
        for col in ["date", "open", "high", "low", "close", "volume"]:
            if col in df.columns:
                keep_cols.append(col)
        df = df[keep_cols]

        # Strip timezone info from dates
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)

        # Ensure numeric types
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        # Sort by date
        df = df.sort_values("date").reset_index(drop=True)

        logger.info(
            f"Fetched {ticker}: {len(df)} bars | "
            f"{df['date'].iloc[0].strftime('%Y-%m-%d')} to "
            f"{df['date'].iloc[-1].strftime('%Y-%m-%d')}"
        )

        return df

    except Exception as e:
        logger.error(f"yfinance error for {ticker}: {e}")
        return None
