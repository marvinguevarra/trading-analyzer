"""Tests for output generators — markdown, JSON, and HTML.

Covers:
  - MarkdownGenerator: headers, sections, tables, edge cases
  - JSONGenerator: serialization, pretty/compact, save-to-file
  - HTMLGenerator: structure, theme toggle, collapsible sections, badges
  - generate_report() integration on TradingAnalysisOrchestrator
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.outputs.markdown_generator import MarkdownGenerator, generate_markdown
from src.outputs.json_generator import JSONGenerator, generate_json
from src.outputs.html_generator import HTMLGenerator, generate_html


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def sample_result_full() -> dict:
    """A complete analysis result with all sections populated."""
    return {
        "metadata": {
            "symbol": "WHR",
            "tier": "standard",
            "tier_label": "Standard",
            "bars": 424,
            "timeframe": "1M",
            "date_range": ["1989-01-01", "2024-05-01"],
            "quality_score": 0.98,
        },
        "technical": {
            "current_price": 105.50,
            "gaps": {
                "total": 3,
                "unfilled": 1,
                "gaps": [
                    {
                        "date": "2020-03-01",
                        "type": "gap_down",
                        "gap_pct": 8.5,
                        "gap_low": 95.00,
                        "gap_high": 103.50,
                        "filled": True,
                    },
                    {
                        "date": "2023-07-01",
                        "type": "gap_up",
                        "gap_pct": 3.2,
                        "gap_low": 110.00,
                        "gap_high": 113.52,
                        "filled": False,
                    },
                ],
            },
            "support_resistance": {
                "supports": [
                    {"level": 95.00, "strength": "strong", "distance_pct": -9.95},
                    {"level": 88.50, "strength": "moderate", "distance_pct": -16.11},
                ],
                "resistances": [
                    {"level": 115.00, "strength": "strong", "distance_pct": 9.00},
                    {"level": 130.00, "strength": "weak", "distance_pct": 23.22},
                ],
            },
            "supply_demand": {
                "zones": [
                    {"type": "demand", "low": 90.0, "high": 95.0, "strength": "strong"},
                    {"type": "supply", "low": 120.0, "high": 125.0, "strength": "moderate"},
                ],
            },
        },
        "news": {
            "sentiment_score": 6.5,
            "sentiment_label": "Slightly Bullish",
            "article_count": 12,
            "catalysts": ["earnings_beat", "analyst_upgrade"],
            "key_themes": ["housing market", "margin recovery"],
            "summary": "WHR reported strong Q4 earnings with improved margins.",
            "cost": 0.0007,
        },
        "fundamental": {
            "financial_health": {
                "overall_grade": "B",
                "revenue_trend": "stable",
                "margin_trend": "improving",
                "debt_level": "moderate",
                "cash_flow": "positive",
            },
            "key_risks": [
                "Housing market slowdown",
                "Raw material cost inflation",
            ],
            "opportunities": [
                "Margin expansion from cost cuts",
                "International market growth",
            ],
            "management_commentary": "Management expressed confidence in H2 recovery.",
            "cost": 0.027,
        },
        "synthesis": {
            "bull_case": {
                "factors": ["Margin recovery", "Earnings momentum"],
                "evidence": ["Q4 beat estimates", "Guidance raised"],
            },
            "bear_case": {
                "factors": ["Housing slowdown", "Debt load"],
                "evidence": ["Rising mortgage rates", "2.5x debt/EBITDA"],
            },
            "verdict": "MODERATE_BULL",
            "reasoning": "WHR shows improving fundamentals despite macro headwinds.",
            "risk_reward": {
                "ratio": 2.1,
                "upside_target": "$130",
                "downside_risk": "$90",
            },
            "confidence_explanation": "Moderate confidence based on mixed signals.",
            "cost": 0.135,
        },
        "errors": [],
        "cost_summary": {
            "total_cost": 0.1627,
            "breakdown": {
                "haiku": {"calls": 1, "input_tokens": 500, "output_tokens": 300, "cost": 0.0007},
                "sonnet": {"calls": 1, "input_tokens": 5000, "output_tokens": 1000, "cost": 0.027},
                "opus": {"calls": 1, "input_tokens": 3000, "output_tokens": 800, "cost": 0.135},
            },
            "budget": 3.00,
            "budget_remaining": 2.8373,
            "execution_time_ms": 4567,
            "total_calls": 3,
        },
    }


@pytest.fixture
def sample_result_lite() -> dict:
    """A lite-tier result with only technical + news."""
    return {
        "metadata": {
            "symbol": "AAPL",
            "tier": "lite",
            "tier_label": "Lite",
            "bars": 100,
            "timeframe": "1D",
            "date_range": ["2024-01-01", "2024-05-01"],
        },
        "technical": {
            "current_price": 185.00,
            "gaps": {"total": 0, "unfilled": 0, "gaps": []},
            "support_resistance": {"supports": [], "resistances": []},
            "supply_demand": {"zones": []},
        },
        "news": {
            "sentiment_score": 7.0,
            "sentiment_label": "Bullish",
            "article_count": 5,
            "catalysts": [],
            "key_themes": ["AI spending"],
            "summary": "Apple continues AI investment.",
            "cost": 0.0005,
        },
        "fundamental": {},
        "synthesis": {},
        "errors": [],
        "cost_summary": {
            "total_cost": 0.0005,
            "breakdown": {
                "haiku": {"calls": 1, "input_tokens": 200, "output_tokens": 150, "cost": 0.0005},
            },
            "budget": 0.50,
            "budget_remaining": 0.4995,
            "execution_time_ms": 1200,
            "total_calls": 1,
        },
    }


@pytest.fixture
def sample_result_empty() -> dict:
    """An empty/minimal result (e.g., parse failure)."""
    return {
        "metadata": {"symbol": "BAD", "tier": "lite", "tier_label": "Lite"},
        "technical": {},
        "news": {},
        "fundamental": {},
        "synthesis": {},
        "errors": ["CSV parse failed: file not found"],
        "cost_summary": {
            "total_cost": 0,
            "breakdown": {},
            "budget": 0.50,
            "budget_remaining": 0.50,
            "execution_time_ms": 10,
            "total_calls": 0,
        },
    }


@pytest.fixture
def sample_result_with_errors(sample_result_full) -> dict:
    """A result with some non-fatal errors."""
    result = sample_result_full.copy()
    result["errors"] = [
        "News analysis failed: timeout",
        "SEC fetch failed: rate limited",
    ]
    return result


# ── MarkdownGenerator Tests ───────────────────────────────────


class TestMarkdownGenerator:
    """Tests for MarkdownGenerator."""

    def test_generates_string(self, sample_result_full):
        """Output is a non-empty string."""
        md = generate_markdown(sample_result_full)
        assert isinstance(md, str)
        assert len(md) > 100

    def test_header_contains_symbol(self, sample_result_full):
        """Header includes the stock symbol."""
        md = generate_markdown(sample_result_full)
        assert "# Trading Analysis: WHR" in md

    def test_header_contains_tier(self, sample_result_full):
        """Header includes the tier label."""
        md = generate_markdown(sample_result_full)
        assert "Standard" in md

    def test_metadata_section(self, sample_result_full):
        """Metadata section has bars and timeframe."""
        md = generate_markdown(sample_result_full)
        assert "424" in md
        assert "1M" in md
        assert "1989-01-01" in md

    def test_technical_section_price(self, sample_result_full):
        """Technical section shows current price."""
        md = generate_markdown(sample_result_full)
        assert "$105.50" in md

    def test_technical_section_gaps(self, sample_result_full):
        """Technical section shows gap count."""
        md = generate_markdown(sample_result_full)
        assert "3" in md
        assert "gap_down" in md

    def test_technical_section_support_resistance(self, sample_result_full):
        """Technical section shows S/R levels."""
        md = generate_markdown(sample_result_full)
        assert "$95.00" in md
        assert "$115.00" in md

    def test_technical_section_zones(self, sample_result_full):
        """Technical section shows zones."""
        md = generate_markdown(sample_result_full)
        assert "Demand" in md
        assert "Supply" in md

    def test_news_section(self, sample_result_full):
        """News section shows sentiment and catalysts."""
        md = generate_markdown(sample_result_full)
        assert "6.5/10" in md
        assert "earnings_beat" in md
        assert "housing market" in md

    def test_fundamental_section(self, sample_result_full):
        """Fundamental section shows grade and risks."""
        md = generate_markdown(sample_result_full)
        assert "Overall Grade:** B" in md
        assert "Housing market slowdown" in md
        assert "Margin expansion" in md

    def test_synthesis_section(self, sample_result_full):
        """Synthesis section shows verdict and cases."""
        md = generate_markdown(sample_result_full)
        assert "Moderate Bull" in md
        assert "Margin recovery" in md
        assert "Housing slowdown" in md

    def test_cost_section(self, sample_result_full):
        """Cost section shows totals."""
        md = generate_markdown(sample_result_full)
        assert "$0.1627" in md
        assert "$3.00" in md

    def test_footer(self, sample_result_full):
        """Footer contains disclaimer."""
        md = generate_markdown(sample_result_full)
        assert "Evidence Scorecard" in md

    def test_lite_result_skips_empty_sections(self, sample_result_lite):
        """Lite result doesn't show fundamental or synthesis sections."""
        md = generate_markdown(sample_result_lite)
        assert "# Trading Analysis: AAPL" in md
        assert "Fundamental Analysis" not in md
        assert "Synthesis" not in md

    def test_empty_result_handles_gracefully(self, sample_result_empty):
        """Empty result produces valid output."""
        md = generate_markdown(sample_result_empty)
        assert "# Trading Analysis: BAD" in md
        assert "CSV parse failed" in md

    def test_errors_section(self, sample_result_with_errors):
        """Errors show in warnings section."""
        md = generate_markdown(sample_result_with_errors)
        assert "Warnings" in md
        assert "timeout" in md
        assert "rate limited" in md

    def test_class_and_function_give_same_output(self, sample_result_full):
        """MarkdownGenerator class and convenience function produce same output."""
        from_class = MarkdownGenerator(sample_result_full).generate()
        from_func = generate_markdown(sample_result_full)
        assert from_class == from_func


# ── JSONGenerator Tests ───────────────────────────────────────


class TestJSONGenerator:
    """Tests for JSONGenerator."""

    def test_generates_valid_json(self, sample_result_full):
        """Output is valid JSON."""
        output = generate_json(sample_result_full)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_pretty_print(self, sample_result_full):
        """Pretty mode produces indented JSON."""
        output = generate_json(sample_result_full, pretty=True)
        assert "\n" in output
        assert "  " in output

    def test_compact_print(self, sample_result_full):
        """Compact mode produces single-line JSON."""
        output = generate_json(sample_result_full, pretty=False)
        # Compact JSON should have no leading whitespace (no indentation)
        lines = output.strip().split("\n")
        assert len(lines) == 1

    def test_report_metadata_added(self, sample_result_full):
        """JSON includes _report_metadata."""
        output = generate_json(sample_result_full)
        parsed = json.loads(output)
        meta = parsed["_report_metadata"]
        assert meta["format"] == "json"
        assert meta["generator"] == "trading-analyzer"
        assert "generated_at" in meta

    def test_preserves_all_data(self, sample_result_full):
        """All original data is preserved."""
        output = generate_json(sample_result_full)
        parsed = json.loads(output)
        assert parsed["metadata"]["symbol"] == "WHR"
        assert parsed["technical"]["current_price"] == 105.50
        assert parsed["synthesis"]["verdict"] == "MODERATE_BULL"

    def test_save_to_file(self, sample_result_full, tmp_path):
        """save() writes JSON to disk."""
        gen = JSONGenerator(sample_result_full)
        outpath = str(tmp_path / "test_report.json")
        returned = gen.save(outpath)
        assert returned == outpath
        assert Path(outpath).exists()

        content = Path(outpath).read_text()
        parsed = json.loads(content)
        assert parsed["metadata"]["symbol"] == "WHR"

    def test_save_creates_directories(self, sample_result_full, tmp_path):
        """save() creates parent directories."""
        outpath = str(tmp_path / "nested" / "dir" / "report.json")
        gen = JSONGenerator(sample_result_full)
        gen.save(outpath)
        assert Path(outpath).exists()

    def test_empty_result(self, sample_result_empty):
        """Empty result produces valid JSON."""
        output = generate_json(sample_result_empty)
        parsed = json.loads(output)
        assert parsed["metadata"]["symbol"] == "BAD"

    def test_class_and_function_produce_equivalent_output(self, sample_result_full):
        """JSONGenerator class and convenience function produce equivalent output."""
        from_class = json.loads(JSONGenerator(sample_result_full).generate())
        from_func = json.loads(generate_json(sample_result_full))
        # Remove timestamps that will differ between calls
        from_class.pop("_report_metadata", None)
        from_func.pop("_report_metadata", None)
        assert from_class == from_func


# ── HTMLGenerator Tests ───────────────────────────────────────


class TestHTMLGenerator:
    """Tests for HTMLGenerator."""

    def test_generates_html_document(self, sample_result_full):
        """Output is a complete HTML document."""
        html_output = generate_html(sample_result_full)
        assert html_output.startswith("<!DOCTYPE html>")
        assert "</html>" in html_output

    def test_title_contains_symbol(self, sample_result_full):
        """HTML title contains the symbol."""
        html_output = generate_html(sample_result_full)
        assert "<title>Trading Analysis: WHR</title>" in html_output

    def test_has_embedded_css(self, sample_result_full):
        """CSS is embedded (no external links)."""
        html_output = generate_html(sample_result_full)
        assert "<style>" in html_output
        assert "</style>" in html_output
        assert "stylesheet" not in html_output  # No external CSS

    def test_has_theme_toggle(self, sample_result_full):
        """Has a theme toggle button."""
        html_output = generate_html(sample_result_full)
        assert "toggleTheme" in html_output
        assert "Toggle Theme" in html_output

    def test_has_dark_and_light_themes(self, sample_result_full):
        """CSS includes both dark and light theme variables."""
        html_output = generate_html(sample_result_full)
        assert 'data-theme="dark"' in html_output
        assert '[data-theme="light"]' in html_output

    def test_has_collapsible_sections(self, sample_result_full):
        """Sections have toggle functionality."""
        html_output = generate_html(sample_result_full)
        assert "toggleSection" in html_output
        assert "section-toggle" in html_output

    def test_has_javascript(self, sample_result_full):
        """Embedded JavaScript is present."""
        html_output = generate_html(sample_result_full)
        assert "<script>" in html_output
        assert "</script>" in html_output

    def test_verdict_badge(self, sample_result_full):
        """Verdict has a color-coded badge."""
        html_output = generate_html(sample_result_full)
        assert "badge-bull" in html_output
        assert "Moderate Bull" in html_output

    def test_bear_verdict_badge(self, sample_result_full):
        """Bear verdict uses bear badge class."""
        result = sample_result_full.copy()
        result["synthesis"] = {**result["synthesis"], "verdict": "STRONG_BEAR"}
        html_output = generate_html(result)
        assert "badge-bear" in html_output

    def test_neutral_verdict_badge(self, sample_result_full):
        """Neutral verdict uses neutral badge class."""
        result = sample_result_full.copy()
        result["synthesis"] = {**result["synthesis"], "verdict": "NEUTRAL"}
        html_output = generate_html(result)
        assert "badge-neutral" in html_output

    def test_technical_data_present(self, sample_result_full):
        """Technical data appears in HTML."""
        html_output = generate_html(sample_result_full)
        assert "$105.50" in html_output
        assert "gap_down" in html_output

    def test_news_data_present(self, sample_result_full):
        """News data appears in HTML."""
        html_output = generate_html(sample_result_full)
        assert "6.5/10" in html_output
        assert "earnings_beat" in html_output

    def test_fundamental_data_present(self, sample_result_full):
        """Fundamental data appears in HTML."""
        html_output = generate_html(sample_result_full)
        assert "Overall Grade" in html_output
        assert "Housing market slowdown" in html_output

    def test_cost_data_present(self, sample_result_full):
        """Cost data appears in HTML."""
        html_output = generate_html(sample_result_full)
        assert "$0.1627" in html_output
        assert "4567ms" in html_output

    def test_lite_result(self, sample_result_lite):
        """Lite result generates valid HTML without synthesis."""
        html_output = generate_html(sample_result_lite)
        assert "AAPL" in html_output
        assert "Synthesis" not in html_output

    def test_empty_result(self, sample_result_empty):
        """Empty result produces valid HTML."""
        html_output = generate_html(sample_result_empty)
        assert "BAD" in html_output
        assert "<!DOCTYPE html>" in html_output

    def test_xss_prevention(self):
        """HTML escapes potentially dangerous input."""
        result = {
            "metadata": {"symbol": "<script>alert(1)</script>", "tier": "lite", "tier_label": "Lite"},
            "technical": {},
            "news": {},
            "fundamental": {},
            "synthesis": {},
            "errors": [],
            "cost_summary": {"total_cost": 0, "breakdown": {}, "budget": 1, "budget_remaining": 1, "execution_time_ms": 0, "total_calls": 0},
        }
        html_output = generate_html(result)
        assert "<script>alert(1)</script>" not in html_output
        assert "&lt;script&gt;" in html_output

    def test_responsive_css(self, sample_result_full):
        """CSS includes responsive media query."""
        html_output = generate_html(sample_result_full)
        assert "@media" in html_output

    def test_class_and_function_give_same_output(self, sample_result_full):
        """HTMLGenerator class and convenience function produce same output."""
        from_class = HTMLGenerator(sample_result_full).generate()
        from_func = generate_html(sample_result_full)
        assert from_class == from_func


# ── generate_report() Integration ─────────────────────────────


class TestGenerateReport:
    """Test orchestrator.generate_report() method."""

    def test_generate_markdown_report(self, sample_result_full):
        """generate_report with markdown format."""
        from src.orchestrator import TradingAnalysisOrchestrator

        orchestrator = TradingAnalysisOrchestrator.__new__(TradingAnalysisOrchestrator)
        report = orchestrator.generate_report(sample_result_full, format="markdown")
        assert "# Trading Analysis: WHR" in report

    def test_generate_json_report(self, sample_result_full):
        """generate_report with json format."""
        from src.orchestrator import TradingAnalysisOrchestrator

        orchestrator = TradingAnalysisOrchestrator.__new__(TradingAnalysisOrchestrator)
        report = orchestrator.generate_report(sample_result_full, format="json")
        parsed = json.loads(report)
        assert parsed["metadata"]["symbol"] == "WHR"

    def test_generate_html_report(self, sample_result_full):
        """generate_report with html format."""
        from src.orchestrator import TradingAnalysisOrchestrator

        orchestrator = TradingAnalysisOrchestrator.__new__(TradingAnalysisOrchestrator)
        report = orchestrator.generate_report(sample_result_full, format="html")
        assert "<!DOCTYPE html>" in report

    def test_invalid_format_raises(self, sample_result_full):
        """generate_report raises ValueError for unknown format."""
        from src.orchestrator import TradingAnalysisOrchestrator

        orchestrator = TradingAnalysisOrchestrator.__new__(TradingAnalysisOrchestrator)
        with pytest.raises(ValueError, match="Unknown format"):
            orchestrator.generate_report(sample_result_full, format="pdf")

    def test_save_to_file(self, sample_result_full, tmp_path):
        """generate_report saves to file when output_path given."""
        from src.orchestrator import TradingAnalysisOrchestrator

        orchestrator = TradingAnalysisOrchestrator.__new__(TradingAnalysisOrchestrator)
        outpath = str(tmp_path / "report.md")
        report = orchestrator.generate_report(
            sample_result_full, format="markdown", output_path=outpath
        )
        assert Path(outpath).exists()
        content = Path(outpath).read_text()
        assert "WHR" in content
        assert report == content
