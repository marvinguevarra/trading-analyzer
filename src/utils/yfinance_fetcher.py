"""Yahoo Finance data fetcher.

Fetches OHLCV data via yfinance and normalizes it into the same
ParsedData format used by the CSV parser, enabling ticker-based
analysis through the same orchestrator pipeline.
"""

import pandas as pd
import yfinance as yf

from src.parsers.csv_parser import DataQuality, ParsedData, _assess_quality
from src.utils.logger import get_logger

logger = get_logger("yfinance_fetcher")

# Maps user-facing timeframe strings to yfinance download params.
# period controls how far back to fetch; interval is the bar size.
TIMEFRAME_MAP: dict[str, dict[str, str]] = {
    "1m": {"interval": "1m", "period": "7d"},
    "5m": {"interval": "5m", "period": "60d"},
    "15m": {"interval": "15m", "period": "60d"},
    "1h": {"interval": "1h", "period": "730d"},
    "1d": {"interval": "1d", "period": "2y"},
    "1wk": {"interval": "1wk", "period": "5y"},
    "1mo": {"interval": "1mo", "period": "max"},
}


def fetch_stock_data(ticker: str, timeframe: str = "1d") -> ParsedData:
    """Fetch stock data from Yahoo Finance and return as ParsedData.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT").
        timeframe: Data interval. One of: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo.

    Returns:
        ParsedData with normalized DataFrame and metadata.

    Raises:
        ValueError: If ticker is invalid, timeframe is unsupported,
                    or no data is returned.
    """
    if timeframe not in TIMEFRAME_MAP:
        supported = ", ".join(sorted(TIMEFRAME_MAP.keys()))
        raise ValueError(
            f"Unsupported timeframe '{timeframe}'. Choose from: {supported}"
        )

    params = TIMEFRAME_MAP[timeframe]
    logger.info(
        f"Fetching {ticker} data: interval={params['interval']}, "
        f"period={params['period']}"
    )

    try:
        df = yf.download(
            ticker,
            period=params["period"],
            interval=params["interval"],
            progress=False,
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch data for '{ticker}': {e}") from e

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        raise ValueError(
            f"No data returned for ticker '{ticker}' with timeframe "
            f"'{timeframe}'. Verify the ticker symbol is valid."
        )

    df = _normalize_yfinance_df(df)

    # Quality check
    quality = _assess_quality(df)

    # Date range
    date_range = (
        df["time"].iloc[0].strftime("%Y-%m-%d"),
        df["time"].iloc[-1].strftime("%Y-%m-%d"),
    )

    symbol = ticker.upper()
    logger.info(
        f"Fetched: {symbol} | {timeframe} | {date_range[0]} to "
        f"{date_range[1]} | {len(df)} bars | Quality: {quality.score:.0%}"
    )

    return ParsedData(
        df=df,
        symbol=symbol,
        timeframe=timeframe,
        date_range=date_range,
        quality=quality,
        indicators=[],
    )


def _normalize_yfinance_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance DataFrame to match CSV parser format.

    Converts DatetimeIndex to 'time' column, renames columns to
    lowercase, drops Adj Close, and strips timezone info.
    """
    df = df.copy()

    # Handle MultiIndex columns (yfinance single-ticker quirk)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    # Move index to 'time' column, strip timezone
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "time"})

    # Rename columns to lowercase
    rename = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    df = df.rename(columns=rename)

    # Drop Adj Close if present
    for col in ("Adj Close", "adj close", "adj_close"):
        if col in df.columns:
            df = df.drop(columns=[col])

    # Drop rows where all OHLC values are NaN
    ohlc = ["open", "high", "low", "close"]
    df = df.dropna(subset=ohlc, how="all").reset_index(drop=True)

    # Ensure correct dtypes
    for col in ohlc + ["volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["time"] = pd.to_datetime(df["time"])

    # Sort by time
    df = df.sort_values("time").reset_index(drop=True)

    return df
