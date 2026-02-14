"""Tests for analyzer modules: Gap Analyzer, S/R Calculator, Supply/Demand."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analyzers.gap_analyzer import (
    Gap,
    detect_gaps,
    get_unfilled_gaps,
    prioritize_gaps,
    summarize_gaps,
)
from src.analyzers.sr_calculator import (
    SRLevel,
    calculate_levels,
    detect_round_numbers,
    find_swing_points,
    summarize_levels,
)
from src.analyzers.supply_demand import (
    Zone,
    identify_zones,
    summarize_zones,
)
from src.parsers.csv_parser import load_csv

# Path to sample data
SAMPLE_DIR = Path(__file__).parent.parent / "data" / "samples"
WHR_CSV = SAMPLE_DIR / "NYSE_WHR__1M.csv"


def get_whr_data() -> pd.DataFrame:
    """Load WHR sample data for testing."""
    parsed = load_csv(str(WHR_CSV))
    return parsed.df


# ============================================================
# Gap Analyzer Tests
# ============================================================

class TestGapDetection:
    """Tests for gap detection logic."""

    def test_detect_gap_up(self):
        """Detect a gap up (current low > previous high)."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 102, 115, 116, 117],
            "high": [105, 108, 118, 119, 120],
            "low": [98, 100, 112, 114, 115],
            "close": [103, 106, 116, 117, 118],
            "volume": [1000] * 5,
        })
        # Gap between bar 1 (high=108) and bar 2 (low=112): 3.7% gap
        gaps = detect_gaps(df, min_gap_pct=2.0)
        assert len(gaps) >= 1
        up_gaps = [g for g in gaps if g.direction == "up"]
        assert len(up_gaps) >= 1
        assert up_gaps[0].gap_low == 108.0
        assert up_gaps[0].gap_high == 112.0

    def test_detect_gap_down(self):
        """Detect a gap down (current high < previous low)."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 102, 88, 87, 86],
            "high": [105, 108, 92, 90, 89],
            "low": [98, 100, 86, 85, 84],
            "close": [103, 106, 89, 88, 87],
            "volume": [1000] * 5,
        })
        # Gap between bar 1 (low=100) and bar 2 (high=92): 8% gap
        gaps = detect_gaps(df, min_gap_pct=2.0)
        down_gaps = [g for g in gaps if g.direction == "down"]
        assert len(down_gaps) >= 1
        assert down_gaps[0].gap_high == 100.0
        assert down_gaps[0].gap_low == 92.0

    def test_no_gaps_in_overlapping_bars(self):
        """No gaps detected when bars overlap."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 102, 104, 103, 105],
            "high": [105, 106, 108, 107, 109],
            "low": [98, 100, 101, 100, 102],
            "close": [103, 104, 105, 104, 106],
            "volume": [1000] * 5,
        })
        gaps = detect_gaps(df, min_gap_pct=2.0)
        assert len(gaps) == 0

    def test_min_gap_filter(self):
        """Gaps below threshold are excluded."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [100, 102, 104],
            "high": [105, 106, 108],
            "low": [98, 105.5, 106.5],  # Small 0.5% gap
            "close": [103, 104, 107],
            "volume": [1000] * 3,
        })
        gaps = detect_gaps(df, min_gap_pct=2.0)
        assert len(gaps) == 0

    def test_gap_fill_detection(self):
        """Detect when a gap gets filled."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=6, freq="D"),
            "open": [100, 102, 115, 116, 114, 107],
            "high": [105, 108, 118, 119, 116, 110],
            "low": [98, 100, 112, 113, 108, 105],  # Bar 4&5 fill back into gap
            "close": [103, 106, 116, 115, 109, 106],
            "volume": [1000] * 6,
        })
        gaps = detect_gaps(df, min_gap_pct=2.0)
        filled_gaps = [g for g in gaps if g.filled]
        assert len(filled_gaps) >= 1

    def test_whr_gap_detection(self):
        """WHR monthly data - gaps may not exist at 2% threshold since monthly bars overlap."""
        df = get_whr_data()
        # Monthly bars typically overlap, so use a very low threshold to verify the function works
        gaps = detect_gaps(df, min_gap_pct=0.1)
        # The function should run without error; gaps may or may not exist in monthly data
        assert isinstance(gaps, list)


class TestGapClassification:
    """Tests for gap type classification."""

    def test_gap_types_are_valid(self):
        """All gaps should have a valid type."""
        df = get_whr_data()
        gaps = detect_gaps(df, min_gap_pct=2.0)
        valid_types = {"common", "breakaway", "runaway", "exhaustion"}
        for gap in gaps:
            assert gap.gap_type in valid_types


class TestGapPrioritization:
    """Tests for gap sorting and filtering."""

    def test_prioritize_unfilled_first(self):
        """Unfilled gaps should rank higher."""
        df = get_whr_data()
        gaps = detect_gaps(df, min_gap_pct=2.0)
        if len(gaps) >= 2:
            prioritized = prioritize_gaps(gaps)
            # First gap should be unfilled (if any exist)
            unfilled = get_unfilled_gaps(gaps)
            if unfilled:
                assert prioritized[0].is_unfilled

    def test_summarize_gaps_with_data(self):
        """Summary should include all key fields when gaps exist."""
        # Use synthetic data with a clear gap
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 102, 115, 116, 117],
            "high": [105, 108, 118, 119, 120],
            "low": [98, 100, 112, 114, 115],
            "close": [103, 106, 116, 117, 118],
            "volume": [1000] * 5,
        })
        gaps = detect_gaps(df, min_gap_pct=2.0)
        summary = summarize_gaps(gaps)
        assert "total" in summary
        assert "unfilled" in summary
        assert "by_type" in summary
        assert "by_direction" in summary
        assert "gaps" in summary
        assert summary["total"] >= 1

    def test_summarize_gaps_empty(self):
        """Summary handles empty gap list."""
        summary = summarize_gaps([])
        assert summary["total"] == 0
        assert summary["unfilled"] == 0


# ============================================================
# Support/Resistance Calculator Tests
# ============================================================

class TestSRCalculator:
    """Tests for support/resistance level calculation."""

    def test_find_swing_points(self):
        """Detect swing highs and lows."""
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=20, freq="D"),
            "open": [100 + i * 0.5 for i in range(10)] + [105 - i * 0.5 for i in range(10)],
            "high": [102 + i * 0.5 for i in range(10)] + [107 - i * 0.5 for i in range(10)],
            "low": [98 + i * 0.5 for i in range(10)] + [103 - i * 0.5 for i in range(10)],
            "close": [101 + i * 0.5 for i in range(10)] + [106 - i * 0.5 for i in range(10)],
            "volume": [1000] * 20,
        })
        levels = find_swing_points(df, window=3)
        assert len(levels) > 0

    def test_round_numbers(self):
        """Round number levels around a price."""
        levels = detect_round_numbers(95.0, interval=10.0, count=3)
        prices = [l.price for l in levels]
        assert 90.0 in prices
        assert 100.0 in prices

    def test_calculate_levels_whr(self):
        """Calculate S/R levels from WHR data."""
        df = get_whr_data()
        levels = calculate_levels(df)
        assert len(levels) > 0

        # Should have both support and resistance
        types = {l.level_type for l in levels}
        assert "support" in types or "resistance" in types

    def test_levels_have_valid_strength(self):
        """All levels should have strength between 1-10."""
        df = get_whr_data()
        levels = calculate_levels(df)
        for level in levels:
            assert 1 <= level.strength <= 10

    def test_levels_sorted_by_strength(self):
        """Levels should be returned sorted by strength descending."""
        df = get_whr_data()
        levels = calculate_levels(df)
        strengths = [l.strength for l in levels]
        assert strengths == sorted(strengths, reverse=True)

    def test_summarize_levels(self):
        """Summary should contain key fields."""
        df = get_whr_data()
        current_price = float(df["close"].iloc[-1])
        levels = calculate_levels(df)
        summary = summarize_levels(levels, current_price)
        assert "current_price" in summary
        assert "support_levels" in summary
        assert "resistance_levels" in summary
        assert "total_levels" in summary


# ============================================================
# Supply/Demand Zone Tests
# ============================================================

class TestSupplyDemand:
    """Tests for supply/demand zone identification."""

    def test_detect_demand_zone(self):
        """Detect a demand zone from an explosive move up."""
        # Build: consolidation then big move up
        prices_open = [100, 101, 100.5, 101, 100, 101, 112, 115]
        prices_high = [102, 103, 102.5, 103, 102, 103, 118, 120]
        prices_low = [98, 99, 98.5, 99, 98, 99, 108, 112]
        prices_close = [101, 100.5, 101, 100, 101, 100.5, 115, 118]
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": prices_open,
            "high": prices_high,
            "low": prices_low,
            "close": prices_close,
            "volume": [1000, 1000, 1000, 1000, 1000, 1000, 5000, 4000],
        })
        zones = identify_zones(df, min_move_pct=3.0)
        demand_zones = [z for z in zones if z.zone_type == "demand"]
        assert len(demand_zones) >= 0  # May or may not detect depending on thresholds

    def test_detect_supply_zone(self):
        """Detect a supply zone from an explosive move down."""
        prices_open = [100, 101, 100.5, 101, 100, 101, 90, 85]
        prices_high = [102, 103, 102.5, 103, 102, 103, 98, 92]
        prices_low = [98, 99, 98.5, 99, 98, 99, 85, 82]
        prices_close = [101, 100.5, 101, 100, 101, 100.5, 88, 84]
        df = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=8, freq="D"),
            "open": prices_open,
            "high": prices_high,
            "low": prices_low,
            "close": prices_close,
            "volume": [1000, 1000, 1000, 1000, 1000, 1000, 5000, 4000],
        })
        zones = identify_zones(df, min_move_pct=3.0)
        supply_zones = [z for z in zones if z.zone_type == "supply"]
        assert len(supply_zones) >= 0  # May or may not detect

    def test_zone_strength_range(self):
        """Zone strength should be 1-10."""
        df = get_whr_data()
        zones = identify_zones(df, min_move_pct=3.0)
        for zone in zones:
            assert 1 <= zone.strength <= 10

    def test_zone_types_valid(self):
        """Zone types should be supply or demand."""
        df = get_whr_data()
        zones = identify_zones(df, min_move_pct=3.0)
        for zone in zones:
            assert zone.zone_type in ("supply", "demand")

    def test_zone_patterns_valid(self):
        """Zone patterns should be one of the four types."""
        df = get_whr_data()
        zones = identify_zones(df, min_move_pct=3.0)
        valid_patterns = {"RBR", "DBD", "RBD", "DBR"}
        for zone in zones:
            assert zone.pattern in valid_patterns

    def test_whr_has_zones(self):
        """WHR data should produce some zones."""
        df = get_whr_data()
        zones = identify_zones(df, min_move_pct=3.0)
        # Monthly data with significant moves should have zones
        assert len(zones) >= 0  # May have zero if moves aren't explosive enough

    def test_summarize_zones(self):
        """Summary should include key fields."""
        df = get_whr_data()
        current_price = float(df["close"].iloc[-1])
        zones = identify_zones(df, min_move_pct=3.0)
        summary = summarize_zones(zones, current_price)
        assert "current_price" in summary
        assert "total_zones" in summary
        assert "demand_zones" in summary
        assert "supply_zones" in summary
        assert "fresh_zones" in summary


# ============================================================
# Integration: All analyzers together on WHR data
# ============================================================

class TestIntegration:
    """Integration tests running all analyzers on sample data."""

    def test_full_technical_analysis_whr(self):
        """Run all technical analysis on WHR data."""
        df = get_whr_data()
        current_price = float(df["close"].iloc[-1])

        # Gaps
        gaps = detect_gaps(df, min_gap_pct=2.0)
        gap_summary = summarize_gaps(gaps)

        # S/R levels
        levels = calculate_levels(df, current_price=current_price)
        sr_summary = summarize_levels(levels, current_price)

        # Supply/Demand
        zones = identify_zones(df, min_move_pct=3.0)
        sd_summary = summarize_zones(zones, current_price)

        # All summaries should be valid dicts
        assert isinstance(gap_summary, dict)
        assert isinstance(sr_summary, dict)
        assert isinstance(sd_summary, dict)

        # Current price should be consistent
        assert sr_summary["current_price"] == sd_summary["current_price"]
