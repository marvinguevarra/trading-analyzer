"""Tests for TradingAnalysisOrchestrator.

Tests the end-to-end pipeline with mocked AI agents.
Uses real WHR CSV for technical analysis (no API cost).
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orchestrator import TradingAnalysisOrchestrator
from src.utils.tier_config import TIER_CONFIGS, get_tier_config, list_tiers


# ── Test data ────────────────────────────────────────────────

WHR_CSV = str(Path(__file__).parent.parent / "data" / "samples" / "NYSE_WHR__1M.csv")

MOCK_NEWS_RESULT = {
    "symbol": "WHR",
    "headlines": [{"title": "WHR beats earnings", "date": "2026-02-10", "source": "Reuters"}],
    "sentiment_score": 6.5,
    "sentiment_label": "slightly_bullish",
    "catalysts": ["earnings beat"],
    "key_themes": ["cost optimization"],
    "summary": "Positive sentiment.",
    "article_count": 5,
    "cost": 0.0007,
    "input_tokens": 800,
    "output_tokens": 400,
}

MOCK_FUNDAMENTAL_RESULT = {
    "symbol": "WHR",
    "financial_health": {
        "revenue_trend": "declining",
        "overall_grade": "C",
    },
    "key_risks": ["Housing slowdown"],
    "opportunities": ["Restructuring savings"],
    "management_commentary": "Focused on cost optimization.",
    "key_metrics": {"revenue": "$19.5B"},
    "filing_info": {"type": "10-K", "date": "2026-02-15"},
    "cost": 0.027,
    "input_tokens": 5000,
    "output_tokens": 800,
}

MOCK_SYNTHESIS_RESULT = {
    "symbol": "WHR",
    "bull_case": {
        "factors": ["Earnings beat", "Restructuring savings"],
        "evidence": ["Q4 exceeded expectations", "$300M target"],
    },
    "bear_case": {
        "factors": ["Housing slowdown", "Revenue decline"],
        "evidence": ["Housing starts down", "Revenue -2.3%"],
    },
    "verdict": "MODERATE_BULL",
    "reasoning": "Bull factors outweigh bear factors.",
    "risk_reward": {"ratio": 2.1, "upside_target": "$115", "downside_risk": "$100", "explanation": "2:1"},
    "confidence_explanation": "Moderately strong evidence.",
    "key_levels": {"support": ["$100"], "resistance": ["$115"]},
    "catalysts_to_watch": ["Next earnings"],
    "action_items": ["Consider entry near $100"],
    "cost": 0.135,
    "input_tokens": 3000,
    "output_tokens": 1200,
}


def _patch_agents(orchestrator):
    """Patch all AI agents on an orchestrator to return mock data."""
    if orchestrator._news_agent:
        orchestrator._news_agent.analyze = MagicMock(return_value=MOCK_NEWS_RESULT)
    if orchestrator._fundamental_agent:
        orchestrator._fundamental_agent.analyze = MagicMock(
            return_value=MOCK_FUNDAMENTAL_RESULT
        )
    if orchestrator._synthesis_agent:
        orchestrator._synthesis_agent.synthesize = MagicMock(
            return_value=MOCK_SYNTHESIS_RESULT
        )


# ── Tier config ──────────────────────────────────────────────


class TestTierConfig:
    def test_lite_config(self):
        cfg = get_tier_config("lite")
        assert cfg["include_news"] is True
        assert cfg["include_sec"] is False
        assert cfg["include_synthesis"] is False
        assert cfg["max_cost"] == 0.50

    def test_standard_config(self):
        cfg = get_tier_config("standard")
        assert cfg["include_news"] is True
        assert cfg["include_sec"] is True
        assert cfg["include_synthesis"] is True
        assert cfg["max_cost"] == 3.00

    def test_premium_config(self):
        cfg = get_tier_config("premium")
        assert cfg["extended_thinking"] is True
        assert cfg["max_cost"] == 7.00

    def test_invalid_tier(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            get_tier_config("ultra")

    def test_list_tiers(self):
        tiers = list_tiers()
        assert len(tiers) == 3
        names = [t["name"] for t in tiers]
        assert "lite" in names
        assert "standard" in names
        assert "premium" in names


# ── Orchestrator initialization ──────────────────────────────


class TestOrchestratorInit:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_lite_no_sec_no_synthesis(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        assert orch._news_agent is not None
        assert orch._fundamental_agent is None
        assert orch._synthesis_agent is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_standard_all_agents(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        assert orch._news_agent is not None
        assert orch._fundamental_agent is not None
        assert orch._synthesis_agent is not None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_budget_from_tier(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        assert orch.cost_tracker.budget == 3.00

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_budget_override(self):
        orch = TradingAnalysisOrchestrator(tier="standard", budget=10.0)
        assert orch.cost_tracker.budget == 10.0


# ── Lite tier analysis ───────────────────────────────────────


class TestLiteTier:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_lite_runs_technical_and_news(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        # Technical should be populated (real analysis, no mock needed)
        assert result["technical"]["current_price"] > 0
        # News should be populated (mocked)
        assert result["news"]["sentiment_score"] == 6.5
        # Fundamental and synthesis should be empty
        assert result["fundamental"] == {}
        assert result["synthesis"] == {}

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_lite_metadata(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        assert result["metadata"]["symbol"] == "WHR"
        assert result["metadata"]["tier"] == "lite"
        assert result["metadata"]["bars"] > 0


# ── Standard tier analysis ───────────────────────────────────


class TestStandardTier:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_standard_all_sections_populated(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        assert result["technical"]["current_price"] > 0
        assert result["news"]["sentiment_score"] > 0
        assert result["fundamental"]["financial_health"]["overall_grade"] == "C"
        assert result["synthesis"]["verdict"] == "MODERATE_BULL"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_standard_cost_summary(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        cs = result["cost_summary"]
        assert "total_cost" in cs
        assert "breakdown" in cs
        assert "budget" in cs
        assert "execution_time_ms" in cs
        assert cs["execution_time_ms"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_standard_no_errors(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        assert result["errors"] == []


# ── Error handling ───────────────────────────────────────────


class TestErrorHandling:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_bad_csv_records_error(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze("WHR", "/nonexistent/file.csv")

        assert len(result["errors"]) > 0
        assert "CSV parse failed" in result["errors"][0]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_news_failure_continues(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)
        # Make news fail
        orch._news_agent.analyze = MagicMock(side_effect=Exception("News API down"))

        result = orch.analyze("WHR", WHR_CSV)

        # Should still have technical and other sections
        assert result["technical"]["current_price"] > 0
        assert "News analysis failed" in result["errors"][0]
        # Fundamental and synthesis should still run
        assert result["fundamental"]["financial_health"]["overall_grade"] == "C"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_sec_failure_continues(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)
        orch._fundamental_agent.analyze = MagicMock(
            side_effect=Exception("EDGAR down")
        )

        result = orch.analyze("WHR", WHR_CSV)

        assert result["technical"]["current_price"] > 0
        assert result["news"]["sentiment_score"] > 0
        assert "Fundamental analysis failed" in result["errors"][0]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_synthesis_failure_continues(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)
        orch._synthesis_agent.synthesize = MagicMock(
            side_effect=Exception("Opus rate limited")
        )

        result = orch.analyze("WHR", WHR_CSV)

        assert result["technical"]["current_price"] > 0
        assert result["news"]["sentiment_score"] > 0
        assert result["fundamental"]["financial_health"]["overall_grade"] == "C"
        assert "Synthesis failed" in result["errors"][0]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_all_agents_fail_still_returns_technical(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)
        orch._news_agent.analyze = MagicMock(side_effect=Exception("fail"))
        orch._fundamental_agent.analyze = MagicMock(side_effect=Exception("fail"))
        orch._synthesis_agent.synthesize = MagicMock(side_effect=Exception("fail"))

        result = orch.analyze("WHR", WHR_CSV)

        # Technical should still work (no API calls)
        assert result["technical"]["current_price"] > 0
        assert len(result["errors"]) == 3


# ── Technical analysis (real WHR data) ───────────────────────


class TestTechnicalAnalysis:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_gaps_detected(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        assert "gaps" in result["technical"]
        assert "total" in result["technical"]["gaps"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_sr_levels_detected(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        assert "support_resistance" in result["technical"]

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_zones_detected(self):
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        assert "supply_demand" in result["technical"]


# ── analyze_from_parsed ──────────────────────────────────────


class TestAnalyzeFromParsed:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_works_with_preparsed_data(self):
        from src.parsers.csv_parser import load_csv

        parsed = load_csv(WHR_CSV)
        orch = TradingAnalysisOrchestrator(tier="lite")
        _patch_agents(orch)

        result = orch.analyze_from_parsed("WHR", parsed)

        assert result["technical"]["current_price"] > 0
        assert result["metadata"]["symbol"] == "WHR"
        assert result["metadata"]["tier"] == "lite"


# ── JSON serialization ───────────────────────────────────────


class TestSerialization:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_result_is_json_serializable(self):
        orch = TradingAnalysisOrchestrator(tier="standard")
        _patch_agents(orch)

        result = orch.analyze("WHR", WHR_CSV)

        # This should not raise
        json_str = json.dumps(result, default=str)
        assert len(json_str) > 100

        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["metadata"]["symbol"] == "WHR"
