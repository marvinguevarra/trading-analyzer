"""AI model wrappers for Claude Haiku, Sonnet, and Opus.

Provides a uniform interface for calling different Claude model tiers
with retry logic, cost tracking, and rate limit handling.

Pricing (per 1M tokens):
  Haiku:  $0.25 input / $1.25 output
  Sonnet: $3 input    / $15 output
  Opus:   $15 input   / $75 output
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Optional

import anthropic

from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger

logger = get_logger("model_wrappers")

# Pricing per 1K tokens (divide MTok price by 1000)
PRICING = {
    "haiku": {"input": 0.00025, "output": 0.00125},
    "sonnet": {"input": 0.003, "output": 0.015},
    "opus": {"input": 0.015, "output": 0.075},
}


class BaseModelWrapper(ABC):
    """Abstract base for all Claude model wrappers."""

    tier: str  # "haiku", "sonnet", "opus"
    model_id: str
    default_max_tokens: int

    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        max_retries: int = 3,
    ):
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "No API key provided. Set ANTHROPIC_API_KEY env var "
                "or pass api_key= to the wrapper."
            )
        self.client = anthropic.Anthropic(api_key=resolved_key)
        self.cost_tracker = cost_tracker
        self.max_retries = max_retries

    def call(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        temperature: float = 0.0,
        component: str = "",
    ) -> dict:
        """Send a prompt to the model and return the response.

        Args:
            prompt: The user message to send.
            max_tokens: Max tokens for the response. Uses model default if None.
            system: Optional system prompt.
            temperature: Sampling temperature (0.0 = deterministic).
            component: Caller name for cost tracking attribution.

        Returns:
            dict with keys: text, input_tokens, output_tokens, cost, model
        """
        tokens = max_tokens or self.default_max_tokens

        kwargs: dict = {
            "model": self.model_id,
            "max_tokens": tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self._call_with_retry(**kwargs)

        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self._calculate_cost(input_tokens, output_tokens)

        if self.cost_tracker:
            self.cost_tracker.record_call(
                model=self.tier,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                component=component or self.tier,
                description=prompt[:80],
            )

        logger.info(
            f"{self.tier} | {input_tokens}in/{output_tokens}out | "
            f"${cost:.5f} | {text[:60]}..."
        )

        return {
            "text": text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "model": self.model_id,
        }

    def _call_with_retry(self, **kwargs) -> anthropic.types.Message:
        """Call the API with exponential backoff on retryable errors."""
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self.client.messages.create(**kwargs)
            except anthropic.RateLimitError as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(
                    f"Rate limited (attempt {attempt}/{self.max_retries}), "
                    f"waiting {wait}s..."
                )
                time.sleep(wait)
            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    last_error = e
                    wait = 2 ** attempt
                    logger.warning(
                        f"Server error {e.status_code} (attempt {attempt}/{self.max_retries}), "
                        f"waiting {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    raise

        raise last_error  # type: ignore[misc]

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = PRICING.get(self.tier, PRICING["sonnet"])
        return (input_tokens / 1000 * rates["input"]) + (
            output_tokens / 1000 * rates["output"]
        )

    @abstractmethod
    def _tier_label(self) -> str: ...

    def __repr__(self) -> str:
        return f"<{type(self).__name__} model={self.model_id}>"


class HaikuWrapper(BaseModelWrapper):
    """Claude Haiku 4.5 — fast screening, data parsing, simple lookups."""

    tier = "haiku"
    model_id = "claude-haiku-4-5-20250514"
    default_max_tokens = 4096

    def _tier_label(self) -> str:
        return "haiku"


class SonnetWrapper(BaseModelWrapper):
    """Claude Sonnet 4.5 — core analysis, pattern recognition."""

    tier = "sonnet"
    model_id = "claude-sonnet-4-5-20250929"
    default_max_tokens = 8192

    def _tier_label(self) -> str:
        return "sonnet"


class OpusWrapper(BaseModelWrapper):
    """Claude Opus 4.5 — deep reasoning, thesis validation, synthesis."""

    tier = "opus"
    model_id = "claude-opus-4-5-20251101"
    default_max_tokens = 16384

    def _tier_label(self) -> str:
        return "opus"


def get_wrapper(
    tier: str,
    api_key: Optional[str] = None,
    cost_tracker: Optional[CostTracker] = None,
) -> BaseModelWrapper:
    """Factory function to get a model wrapper by tier name."""
    wrappers = {
        "haiku": HaikuWrapper,
        "sonnet": SonnetWrapper,
        "opus": OpusWrapper,
    }
    cls = wrappers.get(tier.lower())
    if cls is None:
        raise ValueError(f"Unknown tier '{tier}'. Choose from: {list(wrappers)}")
    return cls(api_key=api_key, cost_tracker=cost_tracker)
