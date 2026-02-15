"""SEC EDGAR filing fetcher for fundamental analysis.

Fetches SEC filings (10-K, 10-Q, 8-K) from the EDGAR full-text search API.
Respects SEC rate limits (max 10 requests/second) and includes required
User-Agent header.

SEC EDGAR API docs: https://www.sec.gov/edgar/sec-api-documentation
"""

import gzip
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger("sec_fetcher")

USER_AGENT = "TradingAnalyzer contact@example.com"
EDGAR_COMPANY_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{symbol}%22&dateRange=custom&startdt={start}&enddt={end}&forms={forms}"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}"
EDGAR_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Rate limiter: track last request time
_last_request_time: float = 0.0
_MIN_REQUEST_INTERVAL = 0.12  # ~8 req/sec to stay safely under 10/sec limit


@dataclass
class SECFiling:
    """A single SEC filing record."""

    filing_type: str  # "10-K", "10-Q", "8-K"
    date: str  # Filing date (YYYY-MM-DD)
    accession_number: str
    url: str  # Direct link to filing
    text_content: str  # Extracted text (may be truncated for large filings)
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to plain dict."""
        return {
            "filing_type": self.filing_type,
            "date": self.date,
            "accession_number": self.accession_number,
            "url": self.url,
            "text_content": self.text_content,
            "description": self.description,
        }


def _rate_limit() -> None:
    """Enforce SEC EDGAR rate limit (max 10 requests/second)."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _sec_request(url: str, max_retries: int = 3) -> bytes:
    """Make a rate-limited request to SEC EDGAR.

    Args:
        url: The URL to fetch.
        max_retries: Number of retries on failure.

    Returns:
        Response body as bytes.

    Raises:
        urllib.error.URLError: If all retries fail.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        _rate_limit()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
                # Decompress gzip if server sent compressed response
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.GzipFile(fileobj=BytesIO(raw)).read()
                return raw
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 2 ** attempt
                logger.warning(
                    f"SEC rate limited (attempt {attempt}/{max_retries}), "
                    f"waiting {wait}s"
                )
                time.sleep(wait)
            elif e.code >= 500:
                wait = 2 ** attempt
                logger.warning(
                    f"SEC server error {e.code} (attempt {attempt}/{max_retries}), "
                    f"waiting {wait}s"
                )
                time.sleep(wait)
            else:
                raise
        except urllib.error.URLError as e:
            last_error = e
            logger.warning(
                f"SEC request failed (attempt {attempt}/{max_retries}): {e}"
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    raise last_error  # type: ignore[misc]


def lookup_cik(symbol: str) -> Optional[str]:
    """Look up the CIK number for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "WHR").

    Returns:
        CIK number as zero-padded string, or None if not found.
    """
    logger.info(f"Looking up CIK for {symbol}")
    try:
        data = _sec_request(EDGAR_COMPANY_TICKERS_URL)
        tickers = json.loads(data)

        symbol_upper = symbol.upper()
        for entry in tickers.values():
            if entry.get("ticker", "").upper() == symbol_upper:
                cik = str(entry["cik_str"]).zfill(10)
                logger.info(f"Found CIK for {symbol}: {cik}")
                return cik

        logger.warning(f"CIK not found for symbol: {symbol}")
        return None
    except Exception as e:
        logger.error(f"CIK lookup failed: {e}")
        return None


def fetch_latest_filings(
    symbol: str,
    filing_types: Optional[list[str]] = None,
    max_filings: int = 5,
    max_text_length: int = 100_000,
) -> list[dict]:
    """Fetch recent SEC filings for a stock symbol.

    Uses the SEC EDGAR submissions API to find filings, then fetches
    the primary document text for each.

    Args:
        symbol: Stock ticker symbol (e.g., "WHR").
        filing_types: Filing types to fetch (default: ["10-K", "10-Q"]).
        max_filings: Maximum number of filings to return.
        max_text_length: Maximum characters of text to extract per filing.

    Returns:
        List of filing dicts with keys: filing_type, date, url, text_content,
        accession_number, description.
    """
    if filing_types is None:
        filing_types = ["10-K", "10-Q"]

    logger.info(
        f"Fetching {filing_types} filings for {symbol} (max {max_filings})"
    )

    # Step 1: Look up CIK
    cik = lookup_cik(symbol)
    if cik is None:
        logger.error(f"Cannot fetch filings: CIK not found for {symbol}")
        return []

    # Step 2: Get filing list from submissions API
    try:
        submissions_url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
        data = _sec_request(submissions_url)
        submissions = json.loads(data)
    except Exception as e:
        logger.error(f"Failed to fetch submissions for {symbol}: {e}")
        return []

    # Step 3: Extract matching filings
    recent = submissions.get("filings", {}).get("recent", {})
    if not recent:
        logger.warning(f"No recent filings found for {symbol}")
        return []

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    filings: list[dict] = []
    types_upper = [ft.upper() for ft in filing_types]

    for i in range(len(forms)):
        if forms[i].upper() in types_upper and len(filings) < max_filings:
            accession_clean = accessions[i].replace("-", "")
            doc_url = EDGAR_FILING_URL.format(
                cik=cik.lstrip("0"),
                accession=accession_clean,
                filename=primary_docs[i],
            )

            filing = SECFiling(
                filing_type=forms[i],
                date=dates[i],
                accession_number=accessions[i],
                url=doc_url,
                text_content="",
                description=descriptions[i] if i < len(descriptions) else "",
            )

            # Step 4: Fetch the filing text
            try:
                text = _fetch_filing_text(doc_url, max_text_length)
                filing.text_content = text
            except Exception as e:
                logger.warning(
                    f"Could not fetch text for {forms[i]} "
                    f"({accessions[i]}): {e}"
                )

            filings.append(filing.to_dict())

    logger.info(f"Retrieved {len(filings)} filings for {symbol}")
    return filings


def _fetch_filing_text(url: str, max_length: int = 100_000) -> str:
    """Fetch and extract text from a filing document.

    Handles both HTML and plain text filings. Strips HTML tags and
    truncates to max_length characters.

    Args:
        url: Direct URL to the filing document.
        max_length: Maximum characters to return.

    Returns:
        Extracted text content.
    """
    import re

    data = _sec_request(url)

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    # Strip HTML tags if present
    if "<html" in text.lower() or "<body" in text.lower():
        # Remove script and style blocks
        text = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&nbsp;", " ")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "\n\n[TRUNCATED — full filing available at URL]"
        logger.info(f"Filing text truncated to {max_length} chars")

    return text


def fetch_filing_by_type(
    symbol: str,
    filing_type: str = "10-K",
    max_text_length: int = 100_000,
) -> Optional[dict]:
    """Fetch the most recent filing of a specific type.

    Convenience wrapper around fetch_latest_filings that returns just one.

    Args:
        symbol: Stock ticker symbol.
        filing_type: Type of filing (e.g., "10-K", "10-Q", "8-K").
        max_text_length: Maximum text characters to extract.

    Returns:
        Filing dict, or None if not found.
    """
    filings = fetch_latest_filings(
        symbol=symbol,
        filing_types=[filing_type],
        max_filings=1,
        max_text_length=max_text_length,
    )
    return filings[0] if filings else None
