"""Tests for AnalysisCache."""

import json
import time
from pathlib import Path

import pytest

from src.utils.cache import AnalysisCache


SAMPLE_RESULT = {
    "metadata": {"symbol": "WHR", "tier": "standard"},
    "technical": {"current_price": 91.20},
    "news": {"sentiment_score": 5.5},
    "fundamental": {"financial_health": {"overall_grade": "C"}},
    "synthesis": {"verdict": "NEUTRAL"},
    "cost_summary": {"total_cost": 0.28},
}


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def cache(cache_dir):
    return AnalysisCache(cache_dir=str(cache_dir), ttl_hours=6)


# ── Basic get/set ─────────────────────────────────────────────


class TestGetSet:
    def test_miss_returns_none(self, cache):
        assert cache.get("WHR", "standard") is None

    def test_set_then_get(self, cache):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        result = cache.get("WHR", "standard")
        assert result is not None
        assert result["metadata"]["symbol"] == "WHR"
        assert result["technical"]["current_price"] == 91.20

    def test_cached_flag_on_hit(self, cache):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        result = cache.get("WHR", "standard")
        assert result["cached"] is True
        assert "cache_time" in result
        assert "cache_age_hours" in result

    def test_stored_result_has_cached_false(self, cache, cache_dir):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        # Read the raw file
        files = list(cache_dir.glob("*.json"))
        assert len(files) == 1
        raw = json.loads(files[0].read_text())
        assert raw["cached"] is False

    def test_does_not_mutate_input(self, cache):
        original = dict(SAMPLE_RESULT)
        cache.set("WHR", "standard", original)
        assert "cached" not in SAMPLE_RESULT  # Original not touched


# ── Cache key logic ───────────────────────────────────────────


class TestCacheKeys:
    def test_case_insensitive_symbol(self, cache):
        cache.set("whr", "standard", SAMPLE_RESULT)
        result = cache.get("WHR", "standard")
        assert result is not None

    def test_different_tiers_separate(self, cache):
        cache.set("WHR", "lite", {"tier": "lite"})
        cache.set("WHR", "standard", {"tier": "standard"})
        lite = cache.get("WHR", "lite")
        std = cache.get("WHR", "standard")
        assert lite["tier"] == "lite"
        assert std["tier"] == "standard"

    def test_different_symbols_separate(self, cache):
        cache.set("WHR", "standard", {"sym": "WHR"})
        cache.set("SPY", "standard", {"sym": "SPY"})
        assert cache.get("WHR", "standard")["sym"] == "WHR"
        assert cache.get("SPY", "standard")["sym"] == "SPY"

    def test_filename_format(self, cache, cache_dir):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        files = list(cache_dir.glob("*.json"))
        assert len(files) == 1
        name = files[0].stem
        assert name.startswith("WHR_standard_")


# ── TTL / expiration ──────────────────────────────────────────


class TestTTL:
    def test_fresh_cache_not_expired(self, cache):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        assert cache.get("WHR", "standard") is not None

    def test_expired_cache_returns_none(self, cache_dir):
        short_cache = AnalysisCache(cache_dir=str(cache_dir), ttl_hours=0)
        short_cache.set("WHR", "standard", SAMPLE_RESULT)
        # TTL=0 means immediately expired
        time.sleep(0.1)
        assert short_cache.get("WHR", "standard") is None

    def test_expired_file_is_deleted(self, cache_dir):
        short_cache = AnalysisCache(cache_dir=str(cache_dir), ttl_hours=0)
        short_cache.set("WHR", "standard", SAMPLE_RESULT)
        time.sleep(0.1)
        short_cache.get("WHR", "standard")  # triggers deletion
        assert list(cache_dir.glob("*.json")) == []


# ── Clear ─────────────────────────────────────────────────────


class TestClear:
    def test_clear_all(self, cache):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        cache.set("SPY", "lite", SAMPLE_RESULT)
        count = cache.clear()
        assert count == 2
        assert cache.get("WHR", "standard") is None
        assert cache.get("SPY", "lite") is None

    def test_clear_by_symbol(self, cache):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        cache.set("WHR", "lite", SAMPLE_RESULT)
        cache.set("SPY", "standard", SAMPLE_RESULT)
        count = cache.clear("WHR")
        assert count == 2
        assert cache.get("WHR", "standard") is None
        assert cache.get("SPY", "standard") is not None

    def test_clear_empty_returns_zero(self, cache):
        assert cache.clear() == 0


# ── Stats ─────────────────────────────────────────────────────


class TestStats:
    def test_empty_stats(self, cache):
        s = cache.stats()
        assert s["total_cached"] == 0
        assert s["total_size_mb"] == 0.0
        assert s["symbols"] == {}

    def test_stats_after_caching(self, cache):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        cache.set("SPY", "lite", SAMPLE_RESULT)
        s = cache.stats()
        assert s["total_cached"] == 2
        assert s["total_size_mb"] > 0
        assert s["symbols"] == {"WHR": 1, "SPY": 1}
        assert s["ttl_hours"] == 6


# ── Edge cases ────────────────────────────────────────────────


class TestEdgeCases:
    def test_corrupt_cache_file(self, cache, cache_dir):
        cache.set("WHR", "standard", SAMPLE_RESULT)
        # Corrupt the file
        files = list(cache_dir.glob("*.json"))
        files[0].write_text("not valid json{{{")
        # Should return None and delete corrupt file
        assert cache.get("WHR", "standard") is None
        assert not files[0].exists()

    def test_cache_dir_created_automatically(self, tmp_path):
        new_dir = tmp_path / "nested" / "deep" / "cache"
        c = AnalysisCache(cache_dir=str(new_dir))
        assert new_dir.exists()
        c.set("WHR", "standard", SAMPLE_RESULT)
        assert c.get("WHR", "standard") is not None
