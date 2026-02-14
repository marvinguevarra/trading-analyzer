"""Cost tracking for API usage across Claude model tiers.

Tracks token usage and calculates costs per model. Provides running totals
and budget warnings.

Pricing (per 1K tokens):
  - Haiku:  $0.001 input / $0.005 output
  - Sonnet: $0.003 input / $0.015 output
  - Opus:   $0.015 input / $0.075 output
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger("cost_tracker")

# Default pricing per 1K tokens
DEFAULT_PRICING = {
    "haiku": {"input": 0.001, "output": 0.005},
    "sonnet": {"input": 0.003, "output": 0.015},
    "opus": {"input": 0.015, "output": 0.075},
}


@dataclass
class APICall:
    """Record of a single API call."""

    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime
    component: str
    description: str = ""


@dataclass
class CostTracker:
    """Tracks API costs across an analysis session."""

    budget: Optional[float] = None
    pricing: dict = field(default_factory=lambda: DEFAULT_PRICING.copy())
    calls: list[APICall] = field(default_factory=list)
    _warned_80pct: bool = field(default=False, repr=False)

    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        component: str,
        description: str = "",
    ) -> float:
        """Record an API call and return its cost.

        Args:
            model: Model tier name (haiku, sonnet, opus).
            input_tokens: Number of input tokens used.
            output_tokens: Number of output tokens used.
            component: Which component made the call.
            description: Optional description of what the call did.

        Returns:
            Cost of this call in dollars.
        """
        model_lower = model.lower()
        if model_lower not in self.pricing:
            logger.warning(f"Unknown model '{model}', using sonnet pricing")
            model_lower = "sonnet"

        rates = self.pricing[model_lower]
        cost = (input_tokens / 1000 * rates["input"]) + (
            output_tokens / 1000 * rates["output"]
        )

        call = APICall(
            model=model_lower,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            timestamp=datetime.now(),
            component=component,
            description=description,
        )
        self.calls.append(call)

        logger.info(
            f"API call: {model_lower} | {input_tokens}in/{output_tokens}out | "
            f"${cost:.4f} | {component}: {description}"
        )

        # Budget warnings
        if self.budget and not self._warned_80pct:
            if self.total_cost >= self.budget * 0.8:
                logger.warning(
                    f"Budget 80% reached: ${self.total_cost:.4f} / ${self.budget:.2f}"
                )
                self._warned_80pct = True

        if self.budget and self.total_cost >= self.budget:
            logger.warning(
                f"BUDGET EXCEEDED: ${self.total_cost:.4f} / ${self.budget:.2f}"
            )

        return cost

    @property
    def total_cost(self) -> float:
        """Total cost across all calls."""
        return sum(c.cost for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    def cost_by_model(self) -> dict[str, float]:
        """Break down costs by model."""
        costs: dict[str, float] = {}
        for call in self.calls:
            costs[call.model] = costs.get(call.model, 0) + call.cost
        return costs

    def cost_by_component(self) -> dict[str, float]:
        """Break down costs by component."""
        costs: dict[str, float] = {}
        for call in self.calls:
            costs[call.component] = costs.get(call.component, 0) + call.cost
        return costs

    def estimate_cost(
        self, model: str, estimated_input_tokens: int, estimated_output_tokens: int
    ) -> float:
        """Estimate cost before making a call."""
        model_lower = model.lower()
        rates = self.pricing.get(model_lower, self.pricing["sonnet"])
        return (estimated_input_tokens / 1000 * rates["input"]) + (
            estimated_output_tokens / 1000 * rates["output"]
        )

    def would_exceed_budget(
        self, model: str, estimated_input_tokens: int, estimated_output_tokens: int
    ) -> bool:
        """Check if a planned call would exceed the budget."""
        if not self.budget:
            return False
        estimated = self.estimate_cost(model, estimated_input_tokens, estimated_output_tokens)
        return (self.total_cost + estimated) > self.budget

    def summary(self) -> str:
        """Generate a cost summary string."""
        lines = [
            "=== Cost Summary ===",
            f"Total calls: {len(self.calls)}",
            f"Total tokens: {self.total_input_tokens} input / {self.total_output_tokens} output",
            f"Total cost: ${self.total_cost:.4f}",
        ]
        by_model = self.cost_by_model()
        if by_model:
            lines.append("\nBy model:")
            for model, cost in sorted(by_model.items()):
                model_calls = [c for c in self.calls if c.model == model]
                lines.append(
                    f"  {model}: {len(model_calls)} calls, ${cost:.4f}"
                )
        if self.budget:
            remaining = self.budget - self.total_cost
            lines.append(f"\nBudget: ${self.budget:.2f} | Remaining: ${remaining:.4f}")
        return "\n".join(lines)
