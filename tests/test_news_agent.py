"""Tests for news fetcher and NewsAgent.

All AI calls are mocked — no real API spend in tests.
"""

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.utils.news_fetcher import (
    NewsArticle,
    _parse_rss_date,
    _strip_html,
    clear_cache,
    fetch_recent_news,
    _cache,
)
from src.agents.news_agent import NewsAgent
from src.utils.cost_tracker import CostTracker


# ── Fixtures ─────────────────────────────────────────────────


SAMPLE_ARTICLES = [
    {
        "title": "WHR Reports Strong Q4 Earnings",
        "date": "2026-02-10T14:30:00",
        "url": "https://example.com/whr-q4",
        "snippet": "Whirlpool reported earnings above expectations...",
        "source": "Reuters",
    },
    {
        "title": "Whirlpool Announces Cost Restructuring Plan",
        "date": "2026-02-08T09:00:00",
        "url": "https://example.com/whr-restructuring",
        "snippet": "The appliance maker is cutting costs amid margin pressure...",
        "source": "Bloomberg",
    },
    {
        "title": "Housing Market Slowdown Impacts Appliance Demand",
        "date": "2026-02-05T16:00:00",
        "url": "https://example.com/housing-slowdown",
        "snippet": "New home sales fell 5% last month, dragging appliance stocks...",
        "source": "CNBC",
    },
]

SAMPLE_HAIKU_RESPONSE = json.dumps({
    "sentiment_score": 6.2,
    "sentiment_label": "slightly_bullish",
    "catalysts": ["Q4 earnings beat", "cost restructuring program"],
    "key_themes": ["margin pressure", "housing market impact", "cost optimization"],
    "summary": "WHR news is slightly positive with a strong Q4 earnings beat offset by housing market headwinds. Management's restructuring plan signals proactive cost management.",
    "headline_analysis": [
        {
            "headline": "WHR Reports Strong Q4 Earnings",
            "impact": "positive",
            "relevance": "high",
        },
        {
            "headline": "Whirlpool Announces Cost Restructuring Plan",
            "impact": "neutral",
            "relevance": "high",
        },
        {
            "headline": "Housing Market Slowdown Impacts Appliance Demand",
            "impact": "negative",
            "relevance": "medium",
        },
    ],
})


def _mock_haiku_response(text=SAMPLE_HAIKU_RESPONSE):
    """Create a mock wrapper.call() return value."""
    return {
        "text": text,
        "input_tokens": 800,
        "output_tokens": 400,
        "cost": 0.0007,
        "model": "claude-haiku-4-5-20251001",
    }


@pytest.fixture(autouse=True)
def _clear_news_cache():
    """Clear the news cache before each test."""
    _cache.clear()
    yield
    _cache.clear()


# ── news_fetcher helpers ─────────────────────────────────────


class TestParseRssDate:
    def test_standard_rss_format(self):
        result = _parse_rss_date("Mon, 10 Feb 2026 14:30:00 GMT")
        assert "2026-02-10" in result

    def test_iso_format(self):
        result = _parse_rss_date("2026-02-10T14:30:00Z")
        assert "2026-02-10" in result

    def test_empty_string(self):
        assert _parse_rss_date("") == ""

    def test_unparseable_returns_empty(self):
        assert _parse_rss_date("not a date") == ""


class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_decodes_entities(self):
        assert _strip_html("A &amp; B") == "A & B"
        assert _strip_html("&lt;tag&gt;") == "<tag>"

    def test_plain_text_unchanged(self):
        assert _strip_html("No HTML here") == "No HTML here"


# ── news_fetcher caching ────────────────────────────────────


class TestNewsCaching:
    @patch("src.utils.news_fetcher._fetch_google_news", return_value=SAMPLE_ARTICLES)
    @patch("src.utils.news_fetcher._fetch_yahoo_news", return_value=[])
    def test_cache_hit(self, mock_yahoo, mock_google):
        """Second call should use cache, not fetch again."""
        fetch_recent_news("WHR", days=7)
        fetch_recent_news("WHR", days=7)
        # Google should only be called once
        assert mock_google.call_count == 1

    @patch("src.utils.news_fetcher._fetch_google_news", return_value=SAMPLE_ARTICLES)
    @patch("src.utils.news_fetcher._fetch_yahoo_news", return_value=[])
    def test_cache_bypass(self, mock_yahoo, mock_google):
        """use_cache=False should always fetch."""
        fetch_recent_news("WHR", days=7, use_cache=False)
        fetch_recent_news("WHR", days=7, use_cache=False)
        assert mock_google.call_count == 2

    @patch("src.utils.news_fetcher._fetch_google_news", return_value=SAMPLE_ARTICLES)
    @patch("src.utils.news_fetcher._fetch_yahoo_news", return_value=[])
    def test_clear_cache_specific(self, mock_yahoo, mock_google):
        fetch_recent_news("WHR", days=7)
        clear_cache("WHR")
        assert not any(k.startswith("WHR_") for k in _cache)

    @patch("src.utils.news_fetcher._fetch_google_news", return_value=SAMPLE_ARTICLES)
    @patch("src.utils.news_fetcher._fetch_yahoo_news", return_value=[])
    def test_clear_cache_all(self, mock_yahoo, mock_google):
        fetch_recent_news("WHR", days=7)
        fetch_recent_news("AAPL", days=7)
        clear_cache()
        assert len(_cache) == 0


# ── fetch_recent_news ────────────────────────────────────────


class TestFetchRecentNews:
    @patch("src.utils.news_fetcher._fetch_google_news", return_value=SAMPLE_ARTICLES)
    @patch("src.utils.news_fetcher._fetch_yahoo_news", return_value=[])
    def test_returns_list_of_dicts(self, mock_yahoo, mock_google):
        articles = fetch_recent_news("WHR", days=7)
        assert isinstance(articles, list)
        assert len(articles) > 0
        assert "title" in articles[0]
        assert "date" in articles[0]
        assert "url" in articles[0]
        assert "snippet" in articles[0]

    @patch("src.utils.news_fetcher._fetch_google_news", return_value=SAMPLE_ARTICLES)
    @patch("src.utils.news_fetcher._fetch_yahoo_news", return_value=[])
    def test_deduplicates_by_url(self, mock_yahoo, mock_google):
        # Same articles from both sources would be deduped
        mock_yahoo.return_value = SAMPLE_ARTICLES[:1]
        articles = fetch_recent_news("WHR", days=7)
        urls = [a["url"] for a in articles]
        assert len(urls) == len(set(urls))

    @patch("src.utils.news_fetcher._fetch_google_news", side_effect=Exception("fail"))
    @patch("src.utils.news_fetcher._fetch_yahoo_news", side_effect=Exception("fail"))
    def test_graceful_failure(self, mock_yahoo, mock_google):
        """Both sources failing should return empty list, not crash."""
        articles = fetch_recent_news("INVALID", days=7)
        assert articles == []


# ── NewsAgent ────────────────────────────────────────────────


class TestNewsAgent:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_analyze_returns_expected_keys(self, mock_fetch):
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        result = agent.analyze("WHR")

        assert "headlines" in result
        assert "sentiment_score" in result
        assert "catalysts" in result
        assert "key_themes" in result
        assert "summary" in result
        assert "cost" in result

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_sentiment_score_range(self, mock_fetch):
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        result = agent.analyze("WHR")

        assert 1.0 <= result["sentiment_score"] <= 10.0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_catalysts_are_list(self, mock_fetch):
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        result = agent.analyze("WHR")

        assert isinstance(result["catalysts"], list)
        assert len(result["catalysts"]) > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_key_themes_are_list(self, mock_fetch):
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        result = agent.analyze("WHR")

        assert isinstance(result["key_themes"], list)
        assert len(result["key_themes"]) > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_headlines_match_articles(self, mock_fetch):
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        result = agent.analyze("WHR")

        assert len(result["headlines"]) == len(SAMPLE_ARTICLES)
        assert result["headlines"][0]["title"] == SAMPLE_ARTICLES[0]["title"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_cost_tracking(self, mock_fetch):
        tracker = CostTracker()
        agent = NewsAgent(cost_tracker=tracker)
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        result = agent.analyze("WHR")

        assert result["cost"] > 0
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=[])
    def test_no_articles_returns_empty(self, mock_fetch):
        agent = NewsAgent()

        result = agent.analyze("INVALID")

        assert result["sentiment_score"] == 5.0
        assert result["catalysts"] == []
        assert result["cost"] == 0.0
        assert result["article_count"] == 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_haiku_called_with_system_prompt(self, mock_fetch):
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        agent.analyze("WHR")

        call_kwargs = agent.haiku.call.call_args[1]
        assert "system" in call_kwargs
        assert "financial news analyst" in call_kwargs["system"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_handles_malformed_json_response(self, mock_fetch):
        """Agent should handle non-JSON responses gracefully."""
        agent = NewsAgent()
        agent.haiku.call = MagicMock(
            return_value=_mock_haiku_response(text="This is not JSON")
        )

        result = agent.analyze("WHR")

        # Should still return valid structure with defaults
        assert result["sentiment_score"] == 5.0
        assert result["catalysts"] == []

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_handles_json_with_code_fences(self, mock_fetch):
        """Agent should handle JSON wrapped in markdown code fences."""
        agent = NewsAgent()
        fenced = f"```json\n{SAMPLE_HAIKU_RESPONSE}\n```"
        agent.haiku.call = MagicMock(
            return_value=_mock_haiku_response(text=fenced)
        )

        result = agent.analyze("WHR")

        assert result["sentiment_score"] == 6.2
        assert len(result["catalysts"]) == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("src.agents.news_agent.fetch_recent_news", return_value=SAMPLE_ARTICLES)
    def test_component_label(self, mock_fetch):
        """Verify the component label is set for cost tracking."""
        agent = NewsAgent()
        agent.haiku.call = MagicMock(return_value=_mock_haiku_response())

        agent.analyze("WHR")

        call_kwargs = agent.haiku.call.call_args[1]
        assert call_kwargs["component"] == "news_agent"
