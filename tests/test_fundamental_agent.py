"""Tests for SEC fetcher and FundamentalAgent.

All AI calls are mocked — no real API spend in tests.
SEC EDGAR calls are also mocked to avoid rate limiting.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.utils.sec_fetcher import (
    SECFiling,
    _fetch_filing_text,
    _rate_limit,
    fetch_filing_by_type,
    fetch_latest_filings,
    lookup_cik,
)
from src.agents.fundamental_agent import FundamentalAgent
from src.utils.cost_tracker import CostTracker


# ── Fixtures ─────────────────────────────────────────────────


SAMPLE_CIK_RESPONSE = json.dumps({
    "0": {"cik_str": 106640, "ticker": "WHR", "title": "WHIRLPOOL CORP /DE/"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}).encode()

SAMPLE_SUBMISSIONS = {
    "cik": "0000106640",
    "name": "WHIRLPOOL CORP /DE/",
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q", "8-K", "10-Q", "4"],
            "filingDate": [
                "2026-02-15",
                "2025-11-01",
                "2025-10-15",
                "2025-08-01",
                "2025-07-01",
            ],
            "accessionNumber": [
                "0001064640-26-000012",
                "0001064640-25-000045",
                "0001064640-25-000040",
                "0001064640-25-000030",
                "0001064640-25-000025",
            ],
            "primaryDocument": [
                "whr-20251231.htm",
                "whr-20250930.htm",
                "whr-8k-20251015.htm",
                "whr-20250630.htm",
                "form4.xml",
            ],
            "primaryDocDescription": [
                "10-K Annual Report",
                "10-Q Quarterly Report",
                "8-K Current Report",
                "10-Q Quarterly Report",
                "Statement of Changes",
            ],
        }
    },
}

SAMPLE_FILING_HTML = """
<html><body>
<h1>WHIRLPOOL CORPORATION</h1>
<h2>ANNUAL REPORT ON FORM 10-K</h2>
<p>Revenue for fiscal year 2025 was $19.5 billion, a decrease of 2.3% from 2024.</p>
<p>Net income was $1.2 billion. Operating margin was 6.1%.</p>
<p>Total debt was $5.8 billion. Cash and equivalents were $1.9 billion.</p>
<h3>Risk Factors</h3>
<p>The housing market slowdown continues to impact appliance demand.</p>
<p>Raw material costs remain elevated, particularly steel and copper.</p>
<p>Supply chain disruptions may affect production capacity.</p>
<h3>Management Discussion</h3>
<p>We continue to focus on cost optimization and portfolio simplification.
Our global restructuring program is expected to deliver $300M in savings.</p>
</body></html>
""".strip()

SAMPLE_SONNET_RESPONSE = json.dumps({
    "financial_health": {
        "revenue_trend": "declining",
        "revenue_latest": "$19.5B",
        "profit_margin_trend": "stable",
        "debt_level": "moderate",
        "cash_position": "adequate",
        "overall_grade": "C",
    },
    "key_risks": [
        "Housing market slowdown reducing appliance demand",
        "Elevated raw material costs (steel, copper)",
        "Supply chain disruptions affecting production",
    ],
    "opportunities": [
        "Cost restructuring expected to deliver $300M savings",
        "Portfolio simplification improving focus",
        "Potential margin expansion from cost optimization",
    ],
    "management_commentary": (
        "Management is focused on cost optimization and portfolio simplification. "
        "The global restructuring program targets $300M in savings, signaling "
        "proactive management of margin pressures."
    ),
    "key_metrics": {
        "revenue": "$19.5B",
        "net_income": "$1.2B",
        "operating_margin": "6.1%",
        "total_debt": "$5.8B",
        "cash": "$1.9B",
    },
    "competitive_position": (
        "Whirlpool maintains a leading global position in home appliances "
        "but faces increasing competition from Asian manufacturers."
    ),
    "filing_quality": "comprehensive",
})


def _mock_sonnet_response(text=SAMPLE_SONNET_RESPONSE):
    """Create a mock wrapper.call() return value."""
    return {
        "text": text,
        "input_tokens": 5000,
        "output_tokens": 800,
        "cost": 0.027,
        "model": "claude-sonnet-4-5-20250929",
    }


# ── SEC Fetcher ──────────────────────────────────────────────


class TestLookupCik:
    @patch("src.utils.sec_fetcher._sec_request", return_value=SAMPLE_CIK_RESPONSE)
    def test_finds_whr(self, mock_req):
        cik = lookup_cik("WHR")
        assert cik == "0000106640"

    @patch("src.utils.sec_fetcher._sec_request", return_value=SAMPLE_CIK_RESPONSE)
    def test_case_insensitive(self, mock_req):
        cik = lookup_cik("whr")
        assert cik == "0000106640"

    @patch("src.utils.sec_fetcher._sec_request", return_value=SAMPLE_CIK_RESPONSE)
    def test_not_found(self, mock_req):
        cik = lookup_cik("ZZZZZ")
        assert cik is None

    @patch("src.utils.sec_fetcher._sec_request", side_effect=Exception("network error"))
    def test_error_returns_none(self, mock_req):
        cik = lookup_cik("WHR")
        assert cik is None


class TestFetchLatestFilings:
    @patch("src.utils.sec_fetcher._fetch_filing_text", return_value="filing text here")
    @patch(
        "src.utils.sec_fetcher._sec_request",
        side_effect=[
            SAMPLE_CIK_RESPONSE,
            json.dumps(SAMPLE_SUBMISSIONS).encode(),
        ],
    )
    def test_returns_10k_filings(self, mock_req, mock_text):
        filings = fetch_latest_filings("WHR", filing_types=["10-K"])
        assert len(filings) == 1
        assert filings[0]["filing_type"] == "10-K"
        assert filings[0]["date"] == "2026-02-15"

    @patch("src.utils.sec_fetcher._fetch_filing_text", return_value="filing text here")
    @patch(
        "src.utils.sec_fetcher._sec_request",
        side_effect=[
            SAMPLE_CIK_RESPONSE,
            json.dumps(SAMPLE_SUBMISSIONS).encode(),
        ],
    )
    def test_returns_10q_filings(self, mock_req, mock_text):
        filings = fetch_latest_filings("WHR", filing_types=["10-Q"])
        assert len(filings) == 2
        assert all(f["filing_type"] == "10-Q" for f in filings)

    @patch("src.utils.sec_fetcher._fetch_filing_text", return_value="filing text")
    @patch(
        "src.utils.sec_fetcher._sec_request",
        side_effect=[
            SAMPLE_CIK_RESPONSE,
            json.dumps(SAMPLE_SUBMISSIONS).encode(),
        ],
    )
    def test_respects_max_filings(self, mock_req, mock_text):
        filings = fetch_latest_filings(
            "WHR", filing_types=["10-K", "10-Q"], max_filings=2
        )
        assert len(filings) <= 2

    @patch("src.utils.sec_fetcher._fetch_filing_text", return_value="text")
    @patch(
        "src.utils.sec_fetcher._sec_request",
        side_effect=[
            SAMPLE_CIK_RESPONSE,
            json.dumps(SAMPLE_SUBMISSIONS).encode(),
        ],
    )
    def test_filing_has_expected_keys(self, mock_req, mock_text):
        filings = fetch_latest_filings("WHR", filing_types=["10-K"])
        assert len(filings) > 0
        f = filings[0]
        assert "filing_type" in f
        assert "date" in f
        assert "url" in f
        assert "text_content" in f
        assert "accession_number" in f

    @patch("src.utils.sec_fetcher.lookup_cik", return_value=None)
    def test_cik_not_found_returns_empty(self, mock_cik):
        filings = fetch_latest_filings("ZZZZZ")
        assert filings == []


class TestFetchFilingByType:
    @patch("src.utils.sec_fetcher._fetch_filing_text", return_value="text")
    @patch(
        "src.utils.sec_fetcher._sec_request",
        side_effect=[
            SAMPLE_CIK_RESPONSE,
            json.dumps(SAMPLE_SUBMISSIONS).encode(),
        ],
    )
    def test_returns_single_filing(self, mock_req, mock_text):
        filing = fetch_filing_by_type("WHR", filing_type="10-K")
        assert filing is not None
        assert filing["filing_type"] == "10-K"

    @patch("src.utils.sec_fetcher.lookup_cik", return_value=None)
    def test_returns_none_if_not_found(self, mock_cik):
        filing = fetch_filing_by_type("ZZZZZ", filing_type="10-K")
        assert filing is None


class TestFetchFilingText:
    @patch(
        "src.utils.sec_fetcher._sec_request",
        return_value=SAMPLE_FILING_HTML.encode(),
    )
    def test_strips_html(self, mock_req):
        text = _fetch_filing_text("https://example.com/filing.htm")
        assert "<html>" not in text
        assert "<body>" not in text
        assert "WHIRLPOOL" in text

    @patch(
        "src.utils.sec_fetcher._sec_request",
        return_value=b"Plain text filing content here.",
    )
    def test_plain_text(self, mock_req):
        text = _fetch_filing_text("https://example.com/filing.txt")
        assert text == "Plain text filing content here."

    @patch(
        "src.utils.sec_fetcher._sec_request",
        return_value=b"x" * 200_000,
    )
    def test_truncation(self, mock_req):
        text = _fetch_filing_text("https://example.com/big.htm", max_length=1000)
        assert len(text) < 1100  # 1000 + truncation message
        assert "TRUNCATED" in text


# ── FundamentalAgent ─────────────────────────────────────────


class TestFundamentalAgent:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_analyze_returns_expected_keys(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze("WHR")

        assert "financial_health" in result
        assert "key_risks" in result
        assert "opportunities" in result
        assert "management_commentary" in result
        assert "key_metrics" in result
        assert "filing_info" in result
        assert "cost" in result

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_financial_health_structure(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze("WHR")
        fh = result["financial_health"]

        assert "revenue_trend" in fh
        assert "overall_grade" in fh
        assert fh["overall_grade"] == "C"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_risks_and_opportunities(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze("WHR")

        assert isinstance(result["key_risks"], list)
        assert len(result["key_risks"]) == 3
        assert isinstance(result["opportunities"], list)
        assert len(result["opportunities"]) == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_filing_info_populated(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze("WHR")

        assert result["filing_info"]["type"] == "10-K"
        assert result["filing_info"]["date"] == "2026-02-15"
        assert result["filing_info"]["text_length"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_cost_tracking(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        tracker = CostTracker()
        agent = FundamentalAgent(cost_tracker=tracker)
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze("WHR")

        assert result["cost"] > 0
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type", return_value=None)
    def test_no_filing_returns_empty(self, mock_fetch):
        agent = FundamentalAgent()

        result = agent.analyze("ZZZZZ")

        assert result["financial_health"]["overall_grade"] == "N/A"
        assert result["key_risks"] == []
        assert result["cost"] == 0.0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_empty_text_returns_empty(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": "",
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        result = agent.analyze("WHR")

        assert result["cost"] == 0.0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_handles_malformed_json_response(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(
            return_value=_mock_sonnet_response(text="Not valid JSON at all")
        )

        result = agent.analyze("WHR")

        # Should return valid structure with defaults
        assert result["financial_health"]["overall_grade"] == "N/A"
        assert result["key_risks"] == []

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_component_label(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        agent.analyze("WHR")

        call_kwargs = agent.sonnet.call.call_args[1]
        assert call_kwargs["component"] == "fundamental_agent"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_sonnet_called_with_system_prompt(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        agent.analyze("WHR")

        call_kwargs = agent.sonnet.call.call_args[1]
        assert "system" in call_kwargs
        assert "fundamental analyst" in call_kwargs["system"]


# ── FundamentalAgent.analyze_multiple ────────────────────────


class TestAnalyzeMultiple:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_analyzes_both_10k_and_10q(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze_multiple("WHR", filing_types=["10-K", "10-Q"])

        assert result["symbol"] == "WHR"
        assert len(result["filings_analyzed"]) == 2
        assert result["total_cost"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.fundamental_agent.fetch_filing_by_type")
    def test_deduplicates_risks(self, mock_fetch):
        mock_fetch.return_value = {
            "filing_type": "10-K",
            "date": "2026-02-15",
            "url": "https://sec.gov/filing",
            "text_content": SAMPLE_FILING_HTML,
            "accession_number": "0001064640-26-000012",
        }

        agent = FundamentalAgent()
        agent.sonnet.call = MagicMock(return_value=_mock_sonnet_response())

        result = agent.analyze_multiple("WHR", filing_types=["10-K", "10-K"])

        # Same risks from same response should be deduped
        assert len(result["combined_risks"]) == 3  # not 6


# ── Live integration test (only with real API key) ───────────


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-your"),
    reason="No real ANTHROPIC_API_KEY set",
)
@pytest.mark.skipif(
    os.environ.get("SKIP_LIVE_TESTS", "1") == "1",
    reason="SKIP_LIVE_TESTS=1 (default)",
)
class TestLiveIntegration:
    def test_sec_cik_lookup(self):
        """Test real CIK lookup for WHR."""
        cik = lookup_cik("WHR")
        assert cik is not None
        assert cik.endswith("106640")

    def test_sec_filing_fetch(self):
        """Test real filing fetch for WHR."""
        filings = fetch_latest_filings("WHR", filing_types=["10-K"], max_filings=1)
        assert len(filings) > 0
        assert filings[0]["filing_type"] == "10-K"
        assert len(filings[0]["text_content"]) > 1000
