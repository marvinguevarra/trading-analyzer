"""Tests for CostTracker with persistence, budget tracking, and summaries."""

import json
from pathlib import Path

import pytest

from src.utils.cost_tracker import APICall, CostTracker, DEFAULT_PRICING


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def tracker():
    """Fresh tracker with no persistence."""
    return CostTracker()


@pytest.fixture
def tmp_log(tmp_path):
    """Return a temporary JSON log path."""
    return tmp_path / "cost_log.json"


# ── record() ─────────────────────────────────────────────────


class TestRecord:
    def test_record_returns_cost(self, tracker):
        cost = tracker.record("haiku", 1000, 1000)
        # 1K * 0.00025 + 1K * 0.00125 = 0.0015
        assert abs(cost - 0.0015) < 1e-9

    def test_record_appends_call(self, tracker):
        tracker.record("sonnet", 500, 200)
        assert len(tracker.calls) == 1
        assert tracker.calls[0].model == "sonnet"
        assert tracker.calls[0].input_tokens == 500
        assert tracker.calls[0].output_tokens == 200

    def test_record_with_component(self, tracker):
        tracker.record("opus", 100, 50, component="gap_analyzer")
        assert tracker.calls[0].component == "gap_analyzer"

    def test_record_with_description(self, tracker):
        tracker.record("haiku", 100, 50, description="test call")
        assert tracker.calls[0].description == "test call"

    def test_record_unknown_model_falls_back_to_sonnet(self, tracker):
        cost = tracker.record("gpt4", 1000, 1000)
        # Should use sonnet pricing: 1K * 0.003 + 1K * 0.015 = 0.018
        assert abs(cost - 0.018) < 1e-9

    def test_record_case_insensitive(self, tracker):
        tracker.record("HAIKU", 1000, 0)
        assert tracker.calls[0].model == "haiku"

    def test_record_call_alias(self, tracker):
        """record_call() is a backward-compat alias for record()."""
        cost = tracker.record_call("haiku", 1000, 1000, component="test")
        assert abs(cost - 0.0015) < 1e-9
        assert len(tracker.calls) == 1


# ── Cost calculations ────────────────────────────────────────


class TestCostCalc:
    def test_haiku_pricing(self, tracker):
        cost = tracker.record("haiku", 1_000_000, 1_000_000)
        # 1M * 0.00025/1K + 1M * 0.00125/1K = 0.25 + 1.25 = 1.50
        assert abs(cost - 1.50) < 1e-6

    def test_sonnet_pricing(self, tracker):
        cost = tracker.record("sonnet", 1_000_000, 1_000_000)
        # 1M * 0.003/1K + 1M * 0.015/1K = 3 + 15 = 18
        assert abs(cost - 18.0) < 1e-6

    def test_opus_pricing(self, tracker):
        cost = tracker.record("opus", 1_000_000, 1_000_000)
        # 1M * 0.015/1K + 1M * 0.075/1K = 15 + 75 = 90
        assert abs(cost - 90.0) < 1e-6

    def test_zero_tokens(self, tracker):
        cost = tracker.record("haiku", 0, 0)
        assert cost == 0.0


# ── get_total_cost() ─────────────────────────────────────────


class TestGetTotalCost:
    def test_empty_tracker(self, tracker):
        assert tracker.get_total_cost() == 0.0

    def test_single_call(self, tracker):
        tracker.record("haiku", 1000, 1000)
        assert abs(tracker.get_total_cost() - 0.0015) < 1e-9

    def test_multiple_calls_accumulate(self, tracker):
        tracker.record("haiku", 1000, 1000)  # 0.0015
        tracker.record("sonnet", 1000, 1000)  # 0.018
        assert abs(tracker.get_total_cost() - 0.0195) < 1e-9

    def test_total_cost_property_matches(self, tracker):
        tracker.record("opus", 500, 250)
        assert tracker.total_cost == tracker.get_total_cost()


# ── get_breakdown() ──────────────────────────────────────────


class TestGetBreakdown:
    def test_empty_tracker(self, tracker):
        assert tracker.get_breakdown() == {}

    def test_single_model(self, tracker):
        tracker.record("haiku", 100, 50)
        bd = tracker.get_breakdown()
        assert "haiku" in bd
        assert bd["haiku"]["calls"] == 1
        assert bd["haiku"]["input_tokens"] == 100
        assert bd["haiku"]["output_tokens"] == 50
        assert bd["haiku"]["cost"] > 0

    def test_multiple_models(self, tracker):
        tracker.record("haiku", 100, 50)
        tracker.record("sonnet", 200, 100)
        tracker.record("opus", 300, 150)
        bd = tracker.get_breakdown()
        assert len(bd) == 3
        assert set(bd.keys()) == {"haiku", "sonnet", "opus"}

    def test_multiple_calls_same_model(self, tracker):
        tracker.record("haiku", 100, 50)
        tracker.record("haiku", 200, 100)
        bd = tracker.get_breakdown()
        assert bd["haiku"]["calls"] == 2
        assert bd["haiku"]["input_tokens"] == 300
        assert bd["haiku"]["output_tokens"] == 150


# ── reset() ──────────────────────────────────────────────────


class TestReset:
    def test_reset_clears_calls(self, tracker):
        tracker.record("haiku", 100, 50)
        tracker.record("sonnet", 200, 100)
        tracker.reset()
        assert len(tracker.calls) == 0
        assert tracker.get_total_cost() == 0.0

    def test_reset_clears_breakdown(self, tracker):
        tracker.record("haiku", 100, 50)
        tracker.reset()
        assert tracker.get_breakdown() == {}

    def test_reset_clears_persisted_file(self, tmp_log):
        tracker = CostTracker(log_path=tmp_log)
        tracker.record("haiku", 100, 50)
        assert tmp_log.exists()
        tracker.reset()
        data = json.loads(tmp_log.read_text())
        assert data["calls"] == []


# ── Persistence ──────────────────────────────────────────────


class TestPersistence:
    def test_saves_on_record(self, tmp_log):
        tracker = CostTracker(log_path=tmp_log)
        tracker.record("haiku", 100, 50)
        assert tmp_log.exists()
        data = json.loads(tmp_log.read_text())
        assert len(data["calls"]) == 1

    def test_load_on_init(self, tmp_log):
        # First tracker records calls
        t1 = CostTracker(log_path=tmp_log)
        t1.record("haiku", 100, 50, component="parser")
        t1.record("sonnet", 200, 100, component="analyzer")

        # Second tracker loads them
        t2 = CostTracker(log_path=tmp_log)
        assert len(t2.calls) == 2
        assert t2.calls[0].model == "haiku"
        assert t2.calls[1].model == "sonnet"
        assert t2.get_total_cost() == t1.get_total_cost()

    def test_load_preserves_components(self, tmp_log):
        t1 = CostTracker(log_path=tmp_log)
        t1.record("opus", 500, 250, component="thesis_validator")
        t2 = CostTracker(log_path=tmp_log)
        assert t2.calls[0].component == "thesis_validator"

    def test_load_preserves_budget(self, tmp_log):
        t1 = CostTracker(budget=5.0, log_path=tmp_log)
        t1.record("haiku", 100, 50)
        t2 = CostTracker(log_path=tmp_log)
        assert t2.budget == 5.0

    def test_no_persistence_without_log_path(self, tracker, tmp_log):
        tracker.record("haiku", 100, 50)
        assert not tmp_log.exists()

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "c" / "cost_log.json"
        tracker = CostTracker(log_path=deep_path)
        tracker.record("haiku", 100, 50)
        assert deep_path.exists()

    def test_handles_corrupt_file(self, tmp_log):
        tmp_log.write_text("not valid json {{{")
        tracker = CostTracker(log_path=tmp_log)
        assert len(tracker.calls) == 0  # graceful fallback

    def test_handles_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.json"
        tracker = CostTracker(log_path=missing)
        assert len(tracker.calls) == 0

    def test_accumulates_across_sessions(self, tmp_log):
        t1 = CostTracker(log_path=tmp_log)
        t1.record("haiku", 100, 50)

        t2 = CostTracker(log_path=tmp_log)
        t2.record("sonnet", 200, 100)

        # t2 should have both calls
        assert len(t2.calls) == 2

        # A third tracker loads all
        t3 = CostTracker(log_path=tmp_log)
        assert len(t3.calls) == 2


# ── Budget ───────────────────────────────────────────────────


class TestBudget:
    def test_no_budget_no_warning(self, tracker, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="trading_analyzer.cost_tracker"):
            tracker.record("opus", 1_000_000, 1_000_000)
        assert "Budget" not in caplog.text
        assert "BUDGET" not in caplog.text

    def test_budget_80pct_warning(self, caplog):
        import logging

        tracker = CostTracker(budget=0.002)
        with caplog.at_level(logging.WARNING, logger="trading_analyzer.cost_tracker"):
            # haiku 1K/1K = $0.0015, which is 75% of $0.002
            tracker.record("haiku", 1000, 1000)
        assert "80%" not in caplog.text

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="trading_analyzer.cost_tracker"):
            # Another call pushes past 80%
            tracker.record("haiku", 1000, 0)
        assert "80%" in caplog.text

    def test_budget_exceeded_warning(self, caplog):
        import logging

        tracker = CostTracker(budget=0.001)
        with caplog.at_level(logging.WARNING, logger="trading_analyzer.cost_tracker"):
            tracker.record("haiku", 1000, 1000)  # $0.0015 > $0.001
        assert "BUDGET EXCEEDED" in caplog.text

    def test_would_exceed_budget(self):
        tracker = CostTracker(budget=0.01)
        tracker.record("haiku", 1000, 1000)  # $0.0015
        # Estimating a big opus call
        assert tracker.would_exceed_budget("opus", 1_000_000, 1_000_000)
        # Small haiku call should be fine
        assert not tracker.would_exceed_budget("haiku", 100, 50)

    def test_would_exceed_no_budget(self, tracker):
        assert not tracker.would_exceed_budget("opus", 1_000_000, 1_000_000)

    def test_estimate_cost(self, tracker):
        est = tracker.estimate_cost("haiku", 1000, 1000)
        assert abs(est - 0.0015) < 1e-9


# ── cost_summary() ───────────────────────────────────────────


class TestCostSummary:
    def test_empty_summary(self, tracker):
        s = tracker.cost_summary()
        assert "Total spent: $0.0000" in s
        assert "Total calls: 0" in s

    def test_summary_with_calls(self, tracker):
        tracker.record("haiku", 1000, 500, component="parser")
        tracker.record("sonnet", 2000, 1000, component="analyzer")
        s = tracker.cost_summary()
        assert "Total spent:" in s
        assert "haiku:" in s
        assert "sonnet:" in s
        assert "Total calls: 2" in s

    def test_summary_with_budget(self):
        tracker = CostTracker(budget=10.0)
        tracker.record("haiku", 1000, 1000)  # $0.0015
        s = tracker.cost_summary()
        assert "Budget: $10.00" in s
        assert "Used:" in s
        assert "Remaining:" in s

    def test_summary_no_budget_line(self, tracker):
        tracker.record("haiku", 100, 50)
        s = tracker.cost_summary()
        assert "Budget:" not in s

    def test_summary_alias(self, tracker):
        """summary() should return the same as cost_summary()."""
        tracker.record("haiku", 100, 50)
        assert tracker.summary() == tracker.cost_summary()


# ── Token totals ─────────────────────────────────────────────


class TestTokenTotals:
    def test_total_input_tokens(self, tracker):
        tracker.record("haiku", 100, 50)
        tracker.record("sonnet", 200, 100)
        assert tracker.total_input_tokens == 300

    def test_total_output_tokens(self, tracker):
        tracker.record("haiku", 100, 50)
        tracker.record("sonnet", 200, 100)
        assert tracker.total_output_tokens == 150


# ── cost_by helpers ──────────────────────────────────────────


class TestCostByHelpers:
    def test_cost_by_model(self, tracker):
        tracker.record("haiku", 1000, 1000)
        tracker.record("sonnet", 1000, 1000)
        by_model = tracker.cost_by_model()
        assert abs(by_model["haiku"] - 0.0015) < 1e-9
        assert abs(by_model["sonnet"] - 0.018) < 1e-9

    def test_cost_by_component(self, tracker):
        tracker.record("haiku", 1000, 1000, component="parser")
        tracker.record("haiku", 1000, 1000, component="analyzer")
        by_comp = tracker.cost_by_component()
        assert "parser" in by_comp
        assert "analyzer" in by_comp
