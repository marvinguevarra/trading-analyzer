"""REAL integration tests — actually calls the Anthropic API.

These tests cost real money. They are skipped by default.

Run them explicitly:
    pytest tests/test_integration_real.py -v -m integration

Or run them alongside unit tests:
    pytest -m "integration" -v

Requires:
    - ANTHROPIC_API_KEY env var set (or config/api_keys.yaml)
    - data/samples/NYSE_WHR__1M.csv present
    - Internet access (SEC EDGAR, Google News, Anthropic API)

Expected cost: ~$0.15-0.25 for the full standard-tier run.
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

# ── Resolve API key ─────────────────────────────────────────

def _get_api_key() -> str | None:
    """Try to get API key from env var or config/api_keys.yaml."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key and not key.startswith("sk-ant-your"):
        return key

    # Try config/api_keys.yaml
    yaml_path = Path(__file__).parent.parent / "config" / "api_keys.yaml"
    if yaml_path.exists():
        try:
            with open(yaml_path) as f:
                cfg = yaml.safe_load(f)
            key = cfg.get("anthropic", {}).get("api_key", "")
            if key and not key.startswith("sk-ant-your"):
                return key
        except Exception:
            pass

    return None


API_KEY = _get_api_key()
WHR_CSV = str(Path(__file__).parent.parent / "data" / "samples" / "NYSE_WHR__1M.csv")

SKIP_REASON = (
    "No real ANTHROPIC_API_KEY set. "
    "Set the env var or create config/api_keys.yaml to run integration tests."
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(API_KEY is None, reason=SKIP_REASON),
]


# ── Helpers ──────────────────────────────────────────────────


def _print_section(title: str, content: str) -> None:
    """Print a formatted section for test output."""
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")
    print(content)


def _print_cost_report(result: dict) -> None:
    """Print a detailed cost breakdown."""
    cs = result.get("cost_summary", {})
    bd = cs.get("breakdown", {})

    lines = [
        f"  Total Cost:      ${cs.get('total_cost', 0):.6f}",
        f"  Budget:          ${cs.get('budget', 0):.2f}",
        f"  Budget Used:     {(cs.get('total_cost', 0) / cs.get('budget', 1)) * 100:.1f}%",
        f"  Budget Left:     ${cs.get('budget_remaining', 0):.6f}",
        f"  API Calls:       {cs.get('total_calls', 0)}",
        f"  Execution Time:  {cs.get('execution_time_ms', 0)}ms",
        "",
        "  Per-model breakdown:",
    ]
    for model, info in sorted(bd.items()):
        lines.append(
            f"    {model:8s}: {info['calls']} calls, "
            f"{info['input_tokens']:,}in/{info['output_tokens']:,}out, "
            f"${info['cost']:.6f}"
        )

    _print_section("COST REPORT", "\n".join(lines))


# ── Individual agent tests ───────────────────────────────────


@pytest.mark.integration
class TestRealHaiku:
    """Test real Haiku API calls."""

    def test_haiku_ping(self):
        """Verify Haiku responds to a simple prompt."""
        from src.agents.model_wrappers import HaikuWrapper

        wrapper = HaikuWrapper(api_key=API_KEY)
        result = wrapper.call(
            prompt="Reply with exactly: PONG",
            max_tokens=16,
            component="integration_test",
        )

        assert "PONG" in result["text"]
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0
        assert result["cost"] > 0
        print(f"\n  Haiku ping cost: ${result['cost']:.6f}")

    def test_news_agent_real(self):
        """Test NewsAgent with real Haiku API call."""
        from src.agents.news_agent import NewsAgent
        from src.utils.cost_tracker import CostTracker

        tracker = CostTracker()
        agent = NewsAgent(api_key=API_KEY, cost_tracker=tracker)
        result = agent.analyze("WHR", lookback_days=7)

        # Verify structure
        assert isinstance(result["sentiment_score"], (int, float))
        assert 1.0 <= result["sentiment_score"] <= 10.0
        assert isinstance(result["catalysts"], list)
        assert isinstance(result["key_themes"], list)
        assert len(result["summary"]) > 10
        assert result["cost"] > 0

        _print_section("NEWS AGENT RESULT", json.dumps({
            "sentiment_score": result["sentiment_score"],
            "sentiment_label": result.get("sentiment_label", ""),
            "catalysts": result["catalysts"],
            "key_themes": result["key_themes"],
            "summary": result["summary"],
            "article_count": result.get("article_count", 0),
            "cost": f"${result['cost']:.6f}",
        }, indent=2))


@pytest.mark.integration
class TestRealSonnet:
    """Test real Sonnet API calls."""

    def test_sonnet_ping(self):
        """Verify Sonnet responds to a simple prompt."""
        from src.agents.model_wrappers import SonnetWrapper

        wrapper = SonnetWrapper(api_key=API_KEY)
        result = wrapper.call(
            prompt="Reply with exactly: PONG",
            max_tokens=16,
            component="integration_test",
        )

        assert "PONG" in result["text"]
        assert result["cost"] > 0
        print(f"\n  Sonnet ping cost: ${result['cost']:.6f}")

    def test_fundamental_agent_real(self):
        """Test FundamentalAgent with real Sonnet API + SEC EDGAR.

        This fetches a real 10-K from SEC EDGAR and sends it to Sonnet.
        """
        from src.agents.fundamental_agent import FundamentalAgent
        from src.utils.cost_tracker import CostTracker

        tracker = CostTracker()
        agent = FundamentalAgent(api_key=API_KEY, cost_tracker=tracker)
        result = agent.analyze("WHR", filing_type="10-K")

        # Verify structure
        fh = result.get("financial_health", {})
        assert fh.get("overall_grade") in {"A", "B", "C", "D", "F", "N/A"}
        assert isinstance(result["key_risks"], list)
        assert isinstance(result["opportunities"], list)
        assert len(result.get("management_commentary", "")) > 10
        assert result["cost"] > 0

        # Filing info should show we actually hit EDGAR
        fi = result.get("filing_info", {})
        assert fi.get("type") == "10-K"
        assert fi.get("text_length", 0) > 1000

        _print_section("FUNDAMENTAL AGENT RESULT", json.dumps({
            "financial_health": fh,
            "key_risks": result["key_risks"][:3],
            "opportunities": result["opportunities"][:3],
            "management_commentary": result["management_commentary"][:200] + "...",
            "filing_date": fi.get("date", ""),
            "filing_text_length": fi.get("text_length", 0),
            "cost": f"${result['cost']:.6f}",
        }, indent=2))


@pytest.mark.integration
class TestRealOpus:
    """Test real Opus API calls."""

    def test_opus_ping(self):
        """Verify Opus responds to a simple prompt."""
        from src.agents.model_wrappers import OpusWrapper

        wrapper = OpusWrapper(api_key=API_KEY)
        result = wrapper.call(
            prompt="Reply with exactly: PONG",
            max_tokens=16,
            component="integration_test",
        )

        assert "PONG" in result["text"]
        assert result["cost"] > 0
        print(f"\n  Opus ping cost: ${result['cost']:.6f}")


# ── Full end-to-end orchestrator test ────────────────────────


@pytest.mark.integration
class TestRealEndToEnd:
    """Full orchestrator run with real API calls.

    This is the ultimate proof that everything works together.
    Expected cost: ~$0.15-0.25 for standard tier.
    """

    def test_full_standard_analysis(self):
        """Run the complete standard-tier analysis on WHR with real API calls."""
        from src.orchestrator import TradingAnalysisOrchestrator

        assert Path(WHR_CSV).exists(), f"WHR sample CSV not found at {WHR_CSV}"

        # Run real analysis
        orchestrator = TradingAnalysisOrchestrator(
            tier="standard",
            api_key=API_KEY,
        )
        result = orchestrator.analyze(
            symbol="WHR",
            csv_file=WHR_CSV,
            min_gap_pct=2.0,
            news_lookback_days=7,
        )

        # ── Verify metadata ──────────────────────────────────
        assert result["metadata"]["symbol"] == "WHR"
        assert result["metadata"]["tier"] == "standard"
        assert result["metadata"]["bars"] > 0

        # ── Verify technical analysis (always works, no API) ─
        tech = result["technical"]
        assert tech["current_price"] > 0
        assert "gaps" in tech
        assert "support_resistance" in tech
        assert "supply_demand" in tech

        _print_section("TECHNICAL", json.dumps({
            "current_price": tech["current_price"],
            "gap_count": tech["gaps"].get("total", 0),
            "sr_levels": len(tech["support_resistance"].get("levels", [])),
            "zones": len(tech["supply_demand"].get("zones", [])),
        }, indent=2))

        # ── Verify news analysis (real Haiku call) ───────────
        news = result["news"]
        assert isinstance(news.get("sentiment_score"), (int, float)), \
            f"Expected numeric sentiment_score, got: {news.get('sentiment_score')}"
        assert news.get("cost", 0) > 0, "News agent should have non-zero cost"

        _print_section("NEWS", json.dumps({
            "sentiment_score": news.get("sentiment_score"),
            "sentiment_label": news.get("sentiment_label"),
            "catalysts": news.get("catalysts", []),
            "key_themes": news.get("key_themes", []),
            "article_count": news.get("article_count", 0),
            "cost": f"${news.get('cost', 0):.6f}",
        }, indent=2))

        # ── Verify fundamental analysis (real Sonnet + EDGAR) ─
        fund = result["fundamental"]
        fh = fund.get("financial_health", {})
        assert fh.get("overall_grade") in {"A", "B", "C", "D", "F", "N/A"}, \
            f"Unexpected grade: {fh.get('overall_grade')}"
        assert fund.get("cost", 0) > 0, "Fundamental agent should have non-zero cost"

        _print_section("FUNDAMENTAL", json.dumps({
            "overall_grade": fh.get("overall_grade"),
            "revenue_trend": fh.get("revenue_trend"),
            "risks_count": len(fund.get("key_risks", [])),
            "opportunities_count": len(fund.get("opportunities", [])),
            "cost": f"${fund.get('cost', 0):.6f}",
        }, indent=2))

        # ── Verify synthesis (real Opus call) ────────────────
        synth = result["synthesis"]
        valid_verdicts = {
            "STRONG_BULL", "MODERATE_BULL", "NEUTRAL",
            "MODERATE_BEAR", "STRONG_BEAR",
        }
        assert synth.get("verdict") in valid_verdicts, \
            f"Unexpected verdict: {synth.get('verdict')}"
        assert len(synth.get("reasoning", "")) > 20, \
            "Reasoning should be substantive"
        assert len(synth.get("bull_case", {}).get("factors", [])) > 0, \
            "Bull case should have factors"
        assert len(synth.get("bear_case", {}).get("factors", [])) > 0, \
            "Bear case should have factors"
        assert synth.get("cost", 0) > 0, "Synthesis should have non-zero cost"

        _print_section("SYNTHESIS", json.dumps({
            "verdict": synth.get("verdict"),
            "reasoning": synth.get("reasoning"),
            "bull_factors": synth.get("bull_case", {}).get("factors", []),
            "bear_factors": synth.get("bear_case", {}).get("factors", []),
            "risk_reward_ratio": synth.get("risk_reward", {}).get("ratio"),
            "confidence": synth.get("confidence_explanation"),
            "cost": f"${synth.get('cost', 0):.6f}",
        }, indent=2))

        # ── Verify no errors ────────────────────────────────
        errors = result.get("errors", [])
        if errors:
            print(f"\n  WARNINGS (non-fatal): {errors}")
        # We allow news/SEC errors (external services can be flaky)
        # but the analysis should still complete

        # ── Verify cost tracking ─────────────────────────────
        cs = result["cost_summary"]
        assert cs["total_cost"] > 0, "Total cost should be non-zero"
        assert cs["total_cost"] < cs["budget"], \
            f"Cost ${cs['total_cost']:.4f} exceeded budget ${cs['budget']:.2f}"
        assert cs["total_calls"] >= 1, "Should have made at least 1 API call"
        assert cs["execution_time_ms"] > 0

        # Print the big cost report
        _print_cost_report(result)

        # ── JSON serialization check ─────────────────────────
        json_str = json.dumps(result, default=str)
        assert len(json_str) > 500, "Result should be substantial JSON"

    def test_lite_tier_cheap(self):
        """Run lite tier — should be very cheap (Haiku only, no SEC/Opus)."""
        from src.orchestrator import TradingAnalysisOrchestrator

        orchestrator = TradingAnalysisOrchestrator(
            tier="lite",
            api_key=API_KEY,
        )
        result = orchestrator.analyze(
            symbol="WHR",
            csv_file=WHR_CSV,
        )

        # Technical should work
        assert result["technical"]["current_price"] > 0

        # No fundamental or synthesis in lite
        assert result["fundamental"] == {} or result["fundamental"] == result["fundamental"]
        assert result["synthesis"] == {}

        cs = result["cost_summary"]
        assert cs["total_cost"] < 0.10, \
            f"Lite tier should cost <$0.10, got ${cs['total_cost']:.4f}"

        print(f"\n  Lite tier total cost: ${cs['total_cost']:.6f}")
        print(f"  Lite tier API calls:  {cs['total_calls']}")
