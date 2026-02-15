"""Tests for NewsAgent (web search-based).

All API calls are mocked — no real API spend in tests.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.agents.news_agent import NewsAgent, WEB_SEARCH_COST
from src.utils.cost_tracker import CostTracker


# ── Fixtures ─────────────────────────────────────────────────


SAMPLE_ANALYSIS_JSON = json.dumps({
    "sentiment_score": 6.2,
    "sentiment_label": "slightly_bullish",
    "catalysts": ["Q4 earnings beat", "cost restructuring program"],
    "key_themes": ["margin pressure", "housing market impact", "cost optimization"],
    "summary": (
        "WHR news is slightly positive with a strong Q4 earnings beat "
        "offset by housing market headwinds."
    ),
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
    "key_developments": [
        "Q4 earnings beat expectations",
        "New restructuring plan announced",
    ],
    "analyst_actions": [
        "Zacks downgrades to Hold",
        "Target price set at $85.43",
    ],
})


def _make_mock_response(text=SAMPLE_ANALYSIS_JSON, input_tokens=800, output_tokens=400):
    """Create a mock anthropic Message response with web search results."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    # Mock web search result
    search_result = MagicMock()
    search_result.type = "web_search_result"
    search_result.title = "WHR Earnings Report"
    search_result.url = "https://example.com/whr-earnings"

    search_block = MagicMock()
    search_block.type = "web_search_tool_result"
    search_block.content = [search_result]

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = [search_block, text_block]
    response.usage = usage
    return response


# ── Tests ────────────────────────────────────────────────────


class TestNewsAgent:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_analyze_returns_expected_keys(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert "headlines" in result
        assert "sentiment_score" in result
        assert "catalysts" in result
        assert "key_themes" in result
        assert "summary" in result
        assert "cost" in result
        assert "sources" in result
        assert "provider" in result
        assert result["provider"] == "claude_web_search"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_sentiment_score_range(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert 1.0 <= result["sentiment_score"] <= 10.0
        assert result["sentiment_score"] == 6.2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_catalysts_are_list(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert isinstance(result["catalysts"], list)
        assert len(result["catalysts"]) == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_key_themes_are_list(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert isinstance(result["key_themes"], list)
        assert len(result["key_themes"]) == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_key_developments(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert isinstance(result["key_developments"], list)
        assert len(result["key_developments"]) == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_analyst_actions(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert isinstance(result["analyst_actions"], list)
        assert len(result["analyst_actions"]) == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_sources_extracted(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        result = agent.analyze("WHR")

        assert isinstance(result["sources"], list)
        assert len(result["sources"]) == 1
        assert result["sources"][0]["url"] == "https://example.com/whr-earnings"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_cost_includes_web_search(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(
            return_value=_make_mock_response(input_tokens=1000, output_tokens=500)
        )

        result = agent.analyze("WHR")

        # Token cost + web search cost
        assert result["cost"] >= WEB_SEARCH_COST
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 500

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_cost_tracking_integration(self):
        tracker = CostTracker()
        agent = NewsAgent(cost_tracker=tracker)
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        agent.analyze("WHR")

        assert len(tracker.calls) == 1
        assert tracker.calls[0].component == "news_agent"
        assert tracker.total_cost > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_api_error_returns_empty(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(
            side_effect=Exception("API error")
        )

        result = agent.analyze("WHR")

        assert result["sentiment_score"] == 5.0
        assert result["catalysts"] == []
        assert "API error" in result["summary"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_handles_malformed_json(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(
            return_value=_make_mock_response(text="Not valid JSON at all")
        )

        result = agent.analyze("WHR")

        # Should return defaults
        assert result["sentiment_score"] == 5.0
        assert result["catalysts"] == []

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_handles_json_with_code_fences(self):
        agent = NewsAgent()
        fenced = f"```json\n{SAMPLE_ANALYSIS_JSON}\n```"
        agent.client.messages.create = MagicMock(
            return_value=_make_mock_response(text=fenced)
        )

        result = agent.analyze("WHR")

        assert result["sentiment_score"] == 6.2
        assert len(result["catalysts"]) == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_web_search_tool_passed(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        agent.analyze("WHR")

        call_kwargs = agent.client.messages.create.call_args[1]
        assert any(
            t.get("type") == "web_search_20250305"
            for t in call_kwargs["tools"]
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_symbol_in_prompt(self):
        agent = NewsAgent()
        agent.client.messages.create = MagicMock(return_value=_make_mock_response())

        agent.analyze("AAPL")

        call_kwargs = agent.client.messages.create.call_args[1]
        user_msg = call_kwargs["messages"][0]["content"]
        assert "AAPL" in user_msg
