"""Cost tracking for API usage across Claude model tiers.

Tracks token usage and calculates costs per model. Provides running totals,
budget warnings, and persists cost history to JSON.

Pricing (per 1M tokens):
  - Haiku:  $0.25 input / $1.25 output
  - Sonnet: $3 input    / $15 output
  - Opus:   $15 input   / $75 output
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger("cost_tracker")

# Default pricing per 1K tokens (MTok price / 1000)
DEFAULT_PRICING = {
    "haiku": {"input": 0.00025, "output": 0.00125},
    "sonnet": {"input": 0.003, "output": 0.015},
    "opus": {"input": 0.015, "output": 0.075},
}

DEFAULT_LOG_PATH = Path("data/cache/cost_log.json")


@dataclass
class APICall:
    """Record of a single API call."""

    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: str  # ISO format string for JSON serialization
    component: str
    description: str = ""


@dataclass
class CostTracker:
    """Tracks API costs across analysis sessions with JSON persistence."""

    budget: Optional[float] = None
    pricing: dict = field(default_factory=lambda: DEFAULT_PRICING.copy())
    calls: list[APICall] = field(default_factory=list)
    log_path: Optional[Path] = field(default=None)
    _warned_80pct: bool = field(default=False, repr=False)

    def __post_init__(self):
        if self.log_path is not None:
            self.log_path = Path(self.log_path)
            self._load()

    # ── Core API (user-requested interface) ───────────────────

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        component: str = "",
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
            timestamp=datetime.now().isoformat(),
            component=component,
            description=description,
        )
        self.calls.append(call)

        logger.info(
            f"API call: {model_lower} | {input_tokens}in/{output_tokens}out | "
            f"${cost:.4f} | {component}: {description}"
        )

        self._check_budget()
        self._save()

        return cost

    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        component: str = "",
        description: str = "",
    ) -> float:
        """Alias for record() — backward compatibility with model_wrappers."""
        return self.record(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            component=component,
            description=description,
        )

    def get_total_cost(self) -> float:
        """Return total cost across all recorded calls."""
        return sum(c.cost for c in self.calls)

    def get_breakdown(self) -> dict:
        """Return per-model cost breakdown.

        Returns:
            Dict mapping model name to {calls, input_tokens, output_tokens, cost}.
        """
        breakdown: dict[str, dict] = {}
        for call in self.calls:
            if call.model not in breakdown:
                breakdown[call.model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            entry = breakdown[call.model]
            entry["calls"] += 1
            entry["input_tokens"] += call.input_tokens
            entry["output_tokens"] += call.output_tokens
            entry["cost"] += call.cost
        return breakdown

    def reset(self) -> None:
        """Clear all recorded calls and reset budget warnings."""
        self.calls.clear()
        self._warned_80pct = False
        self._save()
        logger.info("Cost tracker reset")

    def cost_summary(self) -> str:
        """Human-readable cost summary with budget percentage."""
        total = self.get_total_cost()
        breakdown = self.get_breakdown()

        lines = [
            "=== Cost Summary ===",
            f"Total spent: ${total:.4f}",
            f"Total calls: {len(self.calls)}",
            f"Total tokens: {self.total_input_tokens:,} input / "
            f"{self.total_output_tokens:,} output",
        ]

        if breakdown:
            lines.append("\nPer-model breakdown:")
            for model in sorted(breakdown):
                entry = breakdown[model]
                lines.append(
                    f"  {model}: {entry['calls']} calls, "
                    f"{entry['input_tokens']:,}in/{entry['output_tokens']:,}out, "
                    f"${entry['cost']:.4f}"
                )

        if self.budget:
            pct = (total / self.budget) * 100
            remaining = self.budget - total
            lines.append(
                f"\nBudget: ${self.budget:.2f} | "
                f"Used: {pct:.1f}% | "
                f"Remaining: ${remaining:.4f}"
            )

        return "\n".join(lines)

    # ── Properties (backward compat for model_wrappers tests) ─

    @property
    def total_cost(self) -> float:
        """Total cost across all calls."""
        return self.get_total_cost()

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    # ── Existing helpers ──────────────────────────────────────

    def cost_by_model(self) -> dict[str, float]:
        """Break down costs by model (simple float mapping)."""
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
        estimated = self.estimate_cost(
            model, estimated_input_tokens, estimated_output_tokens
        )
        return (self.total_cost + estimated) > self.budget

    # ── Persistence ───────────────────────────────────────────

    def _save(self) -> None:
        """Persist current calls to JSON file."""
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "calls": [asdict(c) for c in self.calls],
            "budget": self.budget,
        }
        self.log_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        """Load previous calls from JSON file."""
        if self.log_path is None or not self.log_path.exists():
            return
        try:
            data = json.loads(self.log_path.read_text())
            for entry in data.get("calls", []):
                self.calls.append(APICall(**entry))
            if self.budget is None and data.get("budget") is not None:
                self.budget = data["budget"]
            logger.info(
                f"Loaded {len(self.calls)} previous calls from {self.log_path}"
            )
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Could not load cost log: {e}")

    # ── Internal ──────────────────────────────────────────────

    def _check_budget(self) -> None:
        """Emit budget warnings at 80% and 100%."""
        if not self.budget:
            return
        if not self._warned_80pct and self.total_cost >= self.budget * 0.8:
            logger.warning(
                f"Budget 80% reached: ${self.total_cost:.4f} / ${self.budget:.2f}"
            )
            self._warned_80pct = True
        if self.total_cost >= self.budget:
            logger.warning(
                f"BUDGET EXCEEDED: ${self.total_cost:.4f} / ${self.budget:.2f}"
            )

    def summary(self) -> str:
        """Alias for cost_summary() — backward compat."""
        return self.cost_summary()
