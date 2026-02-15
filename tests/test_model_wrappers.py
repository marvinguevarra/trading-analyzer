"""Tests for AI model wrappers."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.agents.model_wrappers import (
    BaseModelWrapper,
    HaikuWrapper,
    OpusWrapper,
    SonnetWrapper,
    get_wrapper,
    PRICING,
)
from src.utils.cost_tracker import CostTracker


# ── Fixtures ─────────────────────────────────────────────────


def _make_mock_response(text="Hello", input_tokens=10, output_tokens=5):
    """Build a fake anthropic Message response."""
    content_block = MagicMock()
    content_block.text = text

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


# ── Class hierarchy ──────────────────────────────────────────


class TestClassHierarchy:
    def test_haiku_is_base(self):
        assert issubclass(HaikuWrapper, BaseModelWrapper)

    def test_sonnet_is_base(self):
        assert issubclass(SonnetWrapper, BaseModelWrapper)

    def test_opus_is_base(self):
        assert issubclass(OpusWrapper, BaseModelWrapper)

    def test_model_ids(self):
        assert HaikuWrapper.model_id == "claude-haiku-4-5-20250514"
        assert SonnetWrapper.model_id == "claude-sonnet-4-5-20250929"
        assert OpusWrapper.model_id == "claude-opus-4-5-20251101"

    def test_tiers(self):
        assert HaikuWrapper.tier == "haiku"
        assert SonnetWrapper.tier == "sonnet"
        assert OpusWrapper.tier == "opus"

    def test_default_max_tokens(self):
        assert HaikuWrapper.default_max_tokens == 4096
        assert SonnetWrapper.default_max_tokens == 8192
        assert OpusWrapper.default_max_tokens == 16384


# ── Factory ──────────────────────────────────────────────────


class TestFactory:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_get_wrapper_haiku(self):
        w = get_wrapper("haiku")
        assert isinstance(w, HaikuWrapper)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_get_wrapper_sonnet(self):
        w = get_wrapper("sonnet")
        assert isinstance(w, SonnetWrapper)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_get_wrapper_opus(self):
        w = get_wrapper("opus")
        assert isinstance(w, OpusWrapper)

    def test_get_wrapper_invalid(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            get_wrapper("gpt4", api_key="sk-test")


# ── API key handling ─────────────────────────────────────────


class TestAPIKey:
    def test_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove key if set
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="No API key"):
                HaikuWrapper()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-env-key"})
    def test_env_key_used(self):
        w = HaikuWrapper()
        assert w.client is not None

    def test_explicit_key_used(self):
        w = HaikuWrapper(api_key="sk-explicit")
        assert w.client is not None


# ── Call with mocked API ─────────────────────────────────────


class TestCall:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_call_returns_expected_keys(self):
        wrapper = HaikuWrapper()
        mock_resp = _make_mock_response("Test reply", 100, 50)
        wrapper.client.messages.create = MagicMock(return_value=mock_resp)

        result = wrapper.call("Hello")

        assert result["text"] == "Test reply"
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["model"] == "claude-haiku-4-5-20250514"
        assert isinstance(result["cost"], float)
        assert result["cost"] > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_call_passes_system_prompt(self):
        wrapper = SonnetWrapper()
        mock_resp = _make_mock_response()
        wrapper.client.messages.create = MagicMock(return_value=mock_resp)

        wrapper.call("Hello", system="You are a trader.")

        call_kwargs = wrapper.client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are a trader."

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_call_respects_max_tokens(self):
        wrapper = HaikuWrapper()
        mock_resp = _make_mock_response()
        wrapper.client.messages.create = MagicMock(return_value=mock_resp)

        wrapper.call("Hello", max_tokens=256)

        call_kwargs = wrapper.client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 256

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_call_uses_default_max_tokens(self):
        wrapper = OpusWrapper()
        mock_resp = _make_mock_response()
        wrapper.client.messages.create = MagicMock(return_value=mock_resp)

        wrapper.call("Hello")

        call_kwargs = wrapper.client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 16384


# ── Cost calculation ─────────────────────────────────────────


class TestCostCalculation:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_haiku_cost(self):
        wrapper = HaikuWrapper()
        cost = wrapper._calculate_cost(1000, 1000)
        # 1K input * 0.00025 + 1K output * 0.00125 = 0.0015
        assert abs(cost - 0.0015) < 1e-9

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_sonnet_cost(self):
        wrapper = SonnetWrapper()
        cost = wrapper._calculate_cost(1000, 1000)
        # 1K * 0.003 + 1K * 0.015 = 0.018
        assert abs(cost - 0.018) < 1e-9

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_opus_cost(self):
        wrapper = OpusWrapper()
        cost = wrapper._calculate_cost(1000, 1000)
        # 1K * 0.015 + 1K * 0.075 = 0.09
        assert abs(cost - 0.09) < 1e-9


# ── Cost tracker integration ────────────────────────────────


class TestCostTrackerIntegration:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_call_records_to_tracker(self):
        tracker = CostTracker()
        wrapper = HaikuWrapper(cost_tracker=tracker)
        mock_resp = _make_mock_response("reply", 200, 100)
        wrapper.client.messages.create = MagicMock(return_value=mock_resp)

        wrapper.call("Test prompt", component="test_component")

        assert len(tracker.calls) == 1
        assert tracker.calls[0].model == "haiku"
        assert tracker.calls[0].component == "test_component"
        assert tracker.total_cost > 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_multiple_calls_accumulate(self):
        tracker = CostTracker()
        wrapper = SonnetWrapper(cost_tracker=tracker)
        mock_resp = _make_mock_response("reply", 100, 50)
        wrapper.client.messages.create = MagicMock(return_value=mock_resp)

        wrapper.call("First")
        wrapper.call("Second")

        assert len(tracker.calls) == 2
        assert tracker.total_input_tokens == 200
        assert tracker.total_output_tokens == 100


# ── Retry logic ──────────────────────────────────────────────


class TestRetry:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_retries_on_rate_limit(self):
        import anthropic as anth

        wrapper = HaikuWrapper(max_retries=2)
        mock_resp = _make_mock_response()

        # First call raises RateLimitError, second succeeds
        rate_err = anth.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        wrapper.client.messages.create = MagicMock(
            side_effect=[rate_err, mock_resp]
        )

        with patch("src.agents.model_wrappers.time.sleep"):
            result = wrapper.call("Hello")

        assert result["text"] == "Hello"
        assert wrapper.client.messages.create.call_count == 2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_raises_after_max_retries(self):
        import anthropic as anth

        wrapper = HaikuWrapper(max_retries=2)

        rate_err = anth.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        wrapper.client.messages.create = MagicMock(
            side_effect=[rate_err, rate_err]
        )

        with patch("src.agents.model_wrappers.time.sleep"):
            with pytest.raises(anth.RateLimitError):
                wrapper.call("Hello")


# ── Live integration test (only runs if API key is set) ──────


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY", "").startswith("sk-ant-your"),
    reason="No real ANTHROPIC_API_KEY set",
)
class TestLiveIntegration:
    def test_haiku_live_call(self):
        wrapper = HaikuWrapper()
        result = wrapper.call(
            "Reply with exactly: PONG",
            max_tokens=16,
            component="live_test",
        )
        assert "PONG" in result["text"]
        assert result["input_tokens"] > 0
        assert result["output_tokens"] > 0
        assert result["cost"] > 0
        print(f"\nLive Haiku cost: ${result['cost']:.6f}")
