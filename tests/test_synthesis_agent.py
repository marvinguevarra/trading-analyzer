"""Tests for SynthesisAgent.

All Opus calls are mocked — no real API spend in tests.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.agents.synthesis_agent import SynthesisAgent
from src.utils.cost_tracker import CostTracker


# ── Fixtures ─────────────────────────────────────────────────


SAMPLE_TECHNICAL = {
    "current_price": 105.50,
    "gaps": {
        "total_gaps": 3,
        "unfilled_gaps": 1,
        "gaps": [
            {"direction": "up", "size_pct": 3.2, "filled": False, "date": "2025-11-01"}
        ],
    },
    "support_resistance": {
        "levels": [
            {"price": 100.0, "type": "support", "strength": 8},
            {"price": 115.0, "type": "resistance", "strength": 7},
        ]
    },
    "supply_demand": {
        "zones": [
            {"type": "demand", "price_low": 98.0, "price_high": 102.0, "fresh": True}
        ]
    },
}

SAMPLE_NEWS = {
    "sentiment_score": 6.2,
    "sentiment_label": "slightly_bullish",
    "catalysts": ["Q4 earnings beat", "cost restructuring"],
    "key_themes": ["margin pressure", "housing market"],
    "summary": "WHR news is slightly positive.",
    "article_count": 10,
    "cost": 0.0007,
}

SAMPLE_FUNDAMENTAL = {
    "financial_health": {
        "revenue_trend": "declining",
        "revenue_latest": "$19.5B",
        "profit_margin_trend": "stable",
        "debt_level": "moderate",
        "cash_position": "adequate",
        "overall_grade": "C",
    },
    "key_risks": ["Housing slowdown", "Raw material costs"],
    "opportunities": ["$300M restructuring savings", "Portfolio simplification"],
    "management_commentary": "Management focused on cost optimization.",
    "key_metrics": {"revenue": "$19.5B", "net_income": "$1.2B"},
    "cost": 0.027,
}

SAMPLE_OPUS_RESPONSE = json.dumps({
    "bull_case": {
        "factors": [
            "Strong demand zone near $100 provides support",
            "Earnings beat signals operational improvement",
            "Restructuring expected to deliver $300M savings",
        ],
        "evidence": [
            "Fresh demand zone at $98-$102 untested",
            "Q4 earnings exceeded expectations",
            "Management confirmed $300M cost savings target",
        ],
    },
    "bear_case": {
        "factors": [
            "Housing market slowdown reducing demand",
            "Revenue declining year-over-year",
            "Elevated raw material costs",
        ],
        "evidence": [
            "Housing starts down 5% last month",
            "Revenue fell 2.3% to $19.5B",
            "Steel and copper prices remain elevated",
        ],
    },
    "verdict": "MODERATE_BULL",
    "reasoning": (
        "While WHR faces headwinds from housing and raw materials, "
        "the strong earnings beat and $300M restructuring program "
        "suggest management is proactively addressing margin pressure. "
        "Technical support near $100 limits downside."
    ),
    "risk_reward": {
        "ratio": 2.1,
        "upside_target": "$115 (resistance level)",
        "downside_risk": "$100 (demand zone support)",
        "explanation": (
            "Upside of ~$10 to resistance vs downside of ~$5 to support "
            "gives approximately 2:1 risk/reward."
        ),
    },
    "confidence_explanation": (
        "Evidence is moderately strong — technical and fundamental data align "
        "on a cautiously bullish outlook, though housing headwinds create uncertainty."
    ),
    "key_levels": {
        "support": ["$100", "$98"],
        "resistance": ["$115"],
    },
    "catalysts_to_watch": ["Next earnings report", "Housing data release"],
    "action_items": [
        "Consider entry near $100-102 demand zone",
        "Set stop loss below $98",
        "Target $115 resistance for profit taking",
    ],
})


def _mock_opus_response(text=SAMPLE_OPUS_RESPONSE):
    """Create a mock wrapper.call() return value."""
    return {
        "text": text,
        "input_tokens": 3000,
        "output_tokens": 1200,
        "cost": 0.135,
        "model": "claude-opus-4-6",
    }


# ── Tests ────────────────────────────────────────────────────


class TestSynthesisAgent:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_synthesize_returns_expected_keys(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize(
            "WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL
        )

        assert "bull_case" in result
        assert "bear_case" in result
        assert "verdict" in result
        assert "reasoning" in result
        assert "risk_reward" in result
        assert "cost" in result

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_bull_case_structure(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize(
            "WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL
        )

        assert "factors" in result["bull_case"]
        assert "evidence" in result["bull_case"]
        assert len(result["bull_case"]["factors"]) == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_bear_case_structure(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize(
            "WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL
        )

        assert "factors" in result["bear_case"]
        assert "evidence" in result["bear_case"]
        assert len(result["bear_case"]["factors"]) == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_verdict_is_valid(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize(
            "WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL
        )

        valid_verdicts = {
            "STRONG_BULL", "MODERATE_BULL", "NEUTRAL",
            "MODERATE_BEAR", "STRONG_BEAR",
        }
        assert result["verdict"] in valid_verdicts

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_risk_reward_structure(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize(
            "WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL
        )

        rr = result["risk_reward"]
        assert "ratio" in rr
        assert isinstance(rr["ratio"], float)
        assert rr["ratio"] > 0
        assert "upside_target" in rr
        assert "downside_risk" in rr

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_cost_tracking(self):
        tracker = CostTracker()
        agent = SynthesisAgent(cost_tracker=tracker)
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize(
            "WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL
        )

        assert result["cost"] > 0
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_handles_partial_data(self):
        """Should work with only technical data (no news/fundamental)."""
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize("WHR", technical_data=SAMPLE_TECHNICAL)

        assert result["verdict"] in {
            "STRONG_BULL", "MODERATE_BULL", "NEUTRAL",
            "MODERATE_BEAR", "STRONG_BEAR",
        }

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_handles_no_data(self):
        """Should handle empty inputs gracefully."""
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize("WHR")

        assert "verdict" in result

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_handles_malformed_json(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(
            return_value=_mock_opus_response(text="Not JSON at all")
        )

        result = agent.synthesize("WHR", SAMPLE_TECHNICAL)

        assert result["verdict"] == "NEUTRAL"
        assert result["bull_case"]["factors"] == []

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_component_label(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        agent.synthesize("WHR", SAMPLE_TECHNICAL)

        call_kwargs = agent.opus.call.call_args[1]
        assert call_kwargs["component"] == "synthesis_agent"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_system_prompt_contains_no_percentages_rule(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        agent.synthesize("WHR", SAMPLE_TECHNICAL)

        call_kwargs = agent.opus.call.call_args[1]
        assert "NEVER give a percentage" in call_kwargs["system"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_confidence_explanation_present(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        result = agent.synthesize("WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS)

        assert "confidence_explanation" in result
        assert len(result["confidence_explanation"]) > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_prompt_includes_all_sections(self):
        agent = SynthesisAgent()
        agent.opus.call = MagicMock(return_value=_mock_opus_response())

        agent.synthesize("WHR", SAMPLE_TECHNICAL, SAMPLE_NEWS, SAMPLE_FUNDAMENTAL)

        call_args = agent.opus.call.call_args
        prompt = call_args[1]["prompt"]
        assert "TECHNICAL ANALYSIS" in prompt
        assert "NEWS ANALYSIS" in prompt
        assert "FUNDAMENTAL ANALYSIS" in prompt
