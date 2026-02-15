"""News fetching for trading analysis.

Fetches recent news articles for a given stock symbol using free RSS feeds
and web sources. Results are cached in-memory for 1 hour to avoid redundant
requests.

Sources:
  - Google News RSS (no API key required)
  - Yahoo Finance RSS (no API key required)
"""

import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger("news_fetcher")

# Cache TTL in seconds (1 hour)
_CACHE_TTL = 3600

# In-memory cache: {symbol: {"timestamp": float, "articles": [...]}}
_cache: dict[str, dict] = {}

USER_AGENT = "TradingAnalyzer/1.0 contact@example.com"


@dataclass
class NewsArticle:
    """A single news article."""

    title: str
    date: str  # ISO format
    url: str
    snippet: str
    source: str = ""

    def to_dict(self) -> dict:
        """Convert to plain dict."""
        return asdict(self)


def fetch_recent_news(
    symbol: str,
    days: int = 7,
    max_articles: int = 20,
    use_cache: bool = True,
) -> list[dict]:
    """Fetch recent news articles for a stock symbol.

    Uses Google News RSS feed (free, no API key required).
    Results are cached in-memory for 1 hour.

    Args:
        symbol: Stock ticker symbol (e.g., "WHR").
        days: Number of days to look back (default 7).
        max_articles: Maximum number of articles to return.
        use_cache: Whether to use cached results (default True).

    Returns:
        List of dicts with keys: title, date, url, snippet, source.
    """
    cache_key = f"{symbol}_{days}"

    # Check cache
    if use_cache and cache_key in _cache:
        cached = _cache[cache_key]
        age = time.time() - cached["timestamp"]
        if age < _CACHE_TTL:
            logger.info(
                f"Cache hit for {symbol} ({len(cached['articles'])} articles, "
                f"{age:.0f}s old)"
            )
            return cached["articles"]

    logger.info(f"Fetching news for {symbol} (last {days} days)")

    articles: list[dict] = []

    # Try Google News RSS
    try:
        google_articles = _fetch_google_news(symbol, days, max_articles)
        articles.extend(google_articles)
    except Exception as e:
        logger.warning(f"Google News fetch failed: {e}")

    # Try Yahoo Finance RSS
    try:
        yahoo_articles = _fetch_yahoo_news(symbol, max_articles)
        articles.extend(yahoo_articles)
    except Exception as e:
        logger.warning(f"Yahoo Finance fetch failed: {e}")

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for article in articles:
        if article["url"] not in seen_urls:
            seen_urls.add(article["url"])
            unique.append(article)
    articles = unique[:max_articles]

    # Sort by date (newest first)
    articles.sort(key=lambda a: a.get("date", ""), reverse=True)

    # Filter to requested time window
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    articles = [a for a in articles if a.get("date", "") >= cutoff or not a["date"]]

    # Update cache
    _cache[cache_key] = {
        "timestamp": time.time(),
        "articles": articles,
    }

    logger.info(f"Found {len(articles)} articles for {symbol}")
    return articles


def clear_cache(symbol: Optional[str] = None) -> None:
    """Clear the news cache.

    Args:
        symbol: Clear cache for specific symbol only. If None, clears all.
    """
    if symbol is None:
        _cache.clear()
        logger.info("News cache cleared (all)")
    else:
        keys_to_remove = [k for k in _cache if k.startswith(f"{symbol}_")]
        for k in keys_to_remove:
            del _cache[k]
        logger.info(f"News cache cleared for {symbol}")


def _fetch_google_news(
    symbol: str, days: int, max_articles: int
) -> list[dict]:
    """Fetch from Google News RSS feed.

    Args:
        symbol: Stock ticker symbol.
        days: Lookback period in days.
        max_articles: Max articles to return.

    Returns:
        List of article dicts.
    """
    query = urllib.request.quote(f"{symbol} stock")
    url = (
        f"https://news.google.com/rss/search?"
        f"q={query}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
    )

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req, timeout=15) as response:
        xml_data = response.read().decode("utf-8")

    root = ET.fromstring(xml_data)
    articles: list[dict] = []

    for item in root.findall(".//item")[:max_articles]:
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        description = item.findtext("description", "")
        source = item.findtext("source", "")

        # Parse RSS date format to ISO
        iso_date = _parse_rss_date(pub_date)

        # Clean HTML from description
        snippet = _strip_html(description)[:500]

        articles.append({
            "title": title,
            "date": iso_date,
            "url": link,
            "snippet": snippet,
            "source": source,
        })

    return articles


def _fetch_yahoo_news(symbol: str, max_articles: int) -> list[dict]:
    """Fetch from Yahoo Finance RSS feed.

    Args:
        symbol: Stock ticker symbol.
        max_articles: Max articles to return.

    Returns:
        List of article dicts.
    """
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req, timeout=15) as response:
        xml_data = response.read().decode("utf-8")

    root = ET.fromstring(xml_data)
    articles: list[dict] = []

    for item in root.findall(".//item")[:max_articles]:
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        description = item.findtext("description", "")

        iso_date = _parse_rss_date(pub_date)
        snippet = _strip_html(description)[:500]

        articles.append({
            "title": title,
            "date": iso_date,
            "url": link,
            "snippet": snippet,
            "source": "Yahoo Finance",
        })

    return articles


def _parse_rss_date(date_str: str) -> str:
    """Parse RSS date formats to ISO 8601 string.

    Args:
        date_str: Date string in RSS format (e.g., "Mon, 10 Feb 2026 14:30:00 GMT").

    Returns:
        ISO format date string, or empty string on failure.
    """
    if not date_str:
        return ""

    # Common RSS date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue

    # Last resort: try to extract just the date
    try:
        # Handle formats like "Mon, 10 Feb 2026 14:30:00 +0000"
        parts = date_str.strip().split()
        if len(parts) >= 4:
            # Try "10 Feb 2026" portion
            day_month_year = " ".join(parts[1:4])
            dt = datetime.strptime(day_month_year, "%d %b %Y")
            return dt.isoformat()
    except (ValueError, IndexError):
        pass

    logger.debug(f"Could not parse date: {date_str}")
    return ""


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string.

    Args:
        text: String potentially containing HTML tags.

    Returns:
        Plain text with tags removed.
    """
    import re

    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("&amp;", "&")
    clean = clean.replace("&lt;", "<")
    clean = clean.replace("&gt;", ">")
    clean = clean.replace("&quot;", '"')
    clean = clean.replace("&#39;", "'")
    clean = clean.replace("&nbsp;", " ")
    return clean.strip()
