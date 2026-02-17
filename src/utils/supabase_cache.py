"""Two-level Supabase cache for SEC filings and fundamental analyses.

Level 1: Raw SEC filing text cached in `sec_filings_cache` table.
Level 2: Claude analysis results cached in `fundamental_analyses_cache` table.

Cache flow:
  1. Check L2 (analysis cache) — instant, $0
  2. Check L1 (filing cache) — fast, skip SEC fetch
  3. Fetch from SEC + analyze with Claude — slow, costs money
  4. Save to both levels for next time

Requires env vars: SUPABASE_URL, SUPABASE_KEY
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger("supabase_cache")

# TTLs in days
ANALYSIS_TTL_DAYS = 90   # Re-analyze quarterly
FILING_TTL_DAYS = 365    # Filings never change

_client = None


def _get_client():
    """Lazy-init Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        logger.debug("Supabase not configured (missing SUPABASE_URL or SUPABASE_KEY)")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase cache connected")
        return _client
    except Exception as e:
        logger.warning(f"Supabase init failed: {e}")
        return None


def _is_expired(cached_at: str, ttl_days: int) -> bool:
    """Check if a cached entry has expired."""
    try:
        cached_time = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - cached_time).days
        return age_days > ttl_days
    except Exception:
        return True


# ── Level 2: Analysis Cache ─────────────────────────────────


def get_cached_analysis(
    ticker: str, filing_period: str
) -> Optional[dict]:
    """Check L2 cache for a previously computed analysis.

    Args:
        ticker: Stock symbol (e.g., "AAPL").
        filing_period: "annual" or "quarterly".

    Returns:
        Cached analysis dict, or None if miss/expired.
    """
    client = _get_client()
    if not client:
        return None

    try:
        result = (
            client.table("fundamental_analyses_cache")
            .select("analysis, cached_at")
            .eq("ticker", ticker.upper())
            .eq("filing_period", filing_period)
            .limit(1)
            .execute()
        )

        if not result.data:
            logger.debug(f"L2 MISS: {ticker} ({filing_period})")
            return None

        row = result.data[0]
        if _is_expired(row["cached_at"], ANALYSIS_TTL_DAYS):
            logger.info(f"L2 EXPIRED: {ticker} ({filing_period})")
            return None

        logger.info(f"L2 HIT: {ticker} ({filing_period})")
        analysis = row["analysis"]
        analysis["_cached"] = True
        analysis["_cached_at"] = row["cached_at"]
        return analysis

    except Exception as e:
        logger.warning(f"L2 cache read failed: {e}")
        return None


def save_analysis(
    ticker: str, filing_period: str, analysis: dict
) -> None:
    """Save analysis result to L2 cache.

    Args:
        ticker: Stock symbol.
        filing_period: "annual" or "quarterly".
        analysis: Full analysis dict from FundamentalAgent.
    """
    client = _get_client()
    if not client:
        return

    try:
        # Strip internal fields before caching
        to_cache = {k: v for k, v in analysis.items() if not k.startswith("_")}

        client.table("fundamental_analyses_cache").upsert({
            "ticker": ticker.upper(),
            "filing_period": filing_period,
            "analysis": to_cache,
        }).execute()

        logger.info(f"L2 SAVED: {ticker} ({filing_period})")
    except Exception as e:
        logger.warning(f"L2 cache write failed: {e}")


# ── Level 1: Filing Cache ───────────────────────────────────


def get_cached_filing(
    ticker: str, filing_type: str
) -> Optional[dict]:
    """Check L1 cache for a previously fetched SEC filing.

    Args:
        ticker: Stock symbol.
        filing_type: Filing type (e.g., "10-K", "20-F").

    Returns:
        Filing dict with text_content, or None if miss/expired.
    """
    client = _get_client()
    if not client:
        return None

    try:
        result = (
            client.table("sec_filings_cache")
            .select("*")
            .eq("ticker", ticker.upper())
            .eq("filing_type", filing_type)
            .limit(1)
            .execute()
        )

        if not result.data:
            logger.debug(f"L1 MISS: {ticker} ({filing_type})")
            return None

        row = result.data[0]
        if _is_expired(row["cached_at"], FILING_TTL_DAYS):
            logger.info(f"L1 EXPIRED: {ticker} ({filing_type})")
            return None

        logger.info(f"L1 HIT: {ticker} ({filing_type})")
        return {
            "filing_type": row["filing_type"],
            "date": row["filing_date"],
            "url": row["filing_url"],
            "text_content": row["text_content"],
            "accession_number": "",
            "_cached": True,
        }

    except Exception as e:
        logger.warning(f"L1 cache read failed: {e}")
        return None


def save_filing(
    ticker: str, filing: dict
) -> None:
    """Save a fetched SEC filing to L1 cache.

    Args:
        ticker: Stock symbol.
        filing: Filing dict from sec_fetcher.
    """
    client = _get_client()
    if not client:
        return

    try:
        client.table("sec_filings_cache").upsert({
            "ticker": ticker.upper(),
            "filing_type": filing.get("filing_type", ""),
            "filing_date": filing.get("date", ""),
            "filing_url": filing.get("url", ""),
            "text_content": filing.get("text_content", ""),
        }).execute()

        logger.info(
            f"L1 SAVED: {ticker} ({filing.get('filing_type', '')}), "
            f"{len(filing.get('text_content', '')):,} chars"
        )
    except Exception as e:
        logger.warning(f"L1 cache write failed: {e}")


# ── Cache Stats ──────────────────────────────────────────────


def cache_stats() -> dict:
    """Get cache statistics."""
    client = _get_client()
    if not client:
        return {"enabled": False, "reason": "Supabase not configured"}

    try:
        filings = client.table("sec_filings_cache").select("ticker", count="exact").execute()
        analyses = client.table("fundamental_analyses_cache").select("ticker", count="exact").execute()

        return {
            "enabled": True,
            "filings_cached": filings.count if filings.count is not None else len(filings.data),
            "analyses_cached": analyses.count if analyses.count is not None else len(analyses.data),
        }
    except Exception as e:
        return {"enabled": True, "error": str(e)}
