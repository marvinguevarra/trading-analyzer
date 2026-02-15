"""Synthesis agent powered by Claude Opus.

Combines technical analysis, news sentiment, and fundamental data into
a unified bull/bear thesis with evidence-based verdict.

Uses the Evidence Scorecard + Checklist Method — NO fake percentages.
Cost target: <$2.00 per synthesis.
"""

import json
from typing import Optional

from src.agents.model_wrappers import get_wrapper
from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger

logger = get_logger("synthesis_agent")

SYNTHESIS_SYSTEM_PROMPT = """\
You are an expert trading analyst performing a synthesis of technical, news,
and fundamental data for a stock. Your job is to combine all evidence into
a clear bull/bear thesis with an actionable verdict.

You MUST respond with valid JSON only — no markdown, no explanation, no code fences.

Your response format:
{
  "bull_case": {
    "factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
    "evidence": ["<specific data point supporting factor 1>", "<data point 2>", "<data point 3>"]
  },
  "bear_case": {
    "factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
    "evidence": ["<specific data point supporting factor 1>", "<data point 2>", "<data point 3>"]
  },
  "verdict": "<STRONG_BULL|MODERATE_BULL|NEUTRAL|MODERATE_BEAR|STRONG_BEAR>",
  "reasoning": "<2-4 sentences explaining the verdict, referencing specific evidence>",
  "risk_reward": {
    "ratio": <float, e.g. 2.5 means 2.5:1 reward to risk>,
    "upside_target": "<price or percentage>",
    "downside_risk": "<price or percentage>",
    "explanation": "<1-2 sentences on how ratio was calculated>"
  },
  "confidence_explanation": "<1-2 sentences explaining how strong the evidence is — do NOT use a percentage>",
  "key_levels": {
    "support": ["<level 1>", "<level 2>"],
    "resistance": ["<level 1>", "<level 2>"]
  },
  "catalysts_to_watch": ["<upcoming event 1>", "<event 2>"],
  "action_items": ["<specific actionable step 1>", "<step 2>"]
}

Rules:
- bull_case and bear_case MUST each have 3-5 factors with matching evidence.
- verdict MUST be one of: STRONG_BULL, MODERATE_BULL, NEUTRAL, MODERATE_BEAR, STRONG_BEAR.
- risk_reward ratio should be calculated from support/resistance levels when available.
- confidence_explanation: Describe the strength and consistency of evidence. NEVER give a percentage.
- Be objective. Present both sides fairly. The verdict should follow from the evidence.
- Only cite facts present in the provided data. Do NOT fabricate numbers.\
"""


class SynthesisAgent:
    """Opus-powered synthesis agent.

    Combines technical analysis, news sentiment, and fundamental data
    into a unified bull/bear thesis with evidence-based verdict.

    Args:
        api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        cost_tracker: Optional CostTracker for budget management.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.opus = get_wrapper("opus", api_key=api_key, cost_tracker=cost_tracker)
        self.cost_tracker = cost_tracker

    def synthesize(
        self,
        symbol: str,
        technical_data: Optional[dict] = None,
        news_data: Optional[dict] = None,
        fundamental_data: Optional[dict] = None,
    ) -> dict:
        """Synthesize all analysis data into a unified thesis.

        Args:
            symbol: Stock ticker symbol (e.g., "WHR").
            technical_data: Output from technical analyzers (gaps, S/R, zones).
            news_data: Output from NewsAgent.analyze().
            fundamental_data: Output from FundamentalAgent.analyze().

        Returns:
            Dict with bull_case, bear_case, verdict, reasoning, risk_reward, cost.
        """
        logger.info(f"Starting synthesis for {symbol}")

        prompt = self._build_prompt(symbol, technical_data, news_data, fundamental_data)

        result = self.opus.call(
            prompt=prompt,
            system=SYNTHESIS_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.0,
            component="synthesis_agent",
        )

        analysis = self._parse_response(result["text"])
        analysis["symbol"] = symbol
        analysis["cost"] = result["cost"]
        analysis["input_tokens"] = result["input_tokens"]
        analysis["output_tokens"] = result["output_tokens"]

        logger.info(
            f"Synthesis complete for {symbol}: "
            f"verdict={analysis['verdict']}, "
            f"cost=${result['cost']:.4f}"
        )

        return analysis

    def _build_prompt(
        self,
        symbol: str,
        technical_data: Optional[dict],
        news_data: Optional[dict],
        fundamental_data: Optional[dict],
    ) -> str:
        """Build the synthesis prompt from all data sources.

        Args:
            symbol: Stock ticker symbol.
            technical_data: Technical analysis results.
            news_data: News analysis results.
            fundamental_data: Fundamental analysis results.

        Returns:
            Formatted prompt string.
        """
        sections: list[str] = [
            f"Synthesize the following analysis data for {symbol} stock.",
            f"Provide a comprehensive bull/bear thesis with verdict.\n",
        ]

        # Technical analysis
        if technical_data:
            sections.append("=== TECHNICAL ANALYSIS ===")
            sections.append(json.dumps(technical_data, indent=2, default=str))
            sections.append("")

        # News analysis
        if news_data:
            # Strip large fields to save tokens
            news_summary = {
                k: v
                for k, v in news_data.items()
                if k not in ("headlines", "headline_analysis", "input_tokens", "output_tokens")
            }
            sections.append("=== NEWS ANALYSIS ===")
            sections.append(json.dumps(news_summary, indent=2, default=str))
            sections.append("")

        # Fundamental analysis
        if fundamental_data:
            fund_summary = {
                k: v
                for k, v in fundamental_data.items()
                if k not in ("filing_info", "input_tokens", "output_tokens")
            }
            sections.append("=== FUNDAMENTAL ANALYSIS ===")
            sections.append(json.dumps(fund_summary, indent=2, default=str))
            sections.append("")

        if not any([technical_data, news_data, fundamental_data]):
            sections.append(
                "No analysis data provided. Generate a general assessment "
                "based on your knowledge of the stock."
            )

        sections.append(
            f"\nProvide your synthesis for {symbol} with bull case, bear case, "
            f"verdict, and risk/reward assessment."
        )

        return "\n".join(sections)

    def _parse_response(self, text: str) -> dict:
        """Parse Opus's JSON response into structured output.

        Args:
            text: Raw response text from Opus.

        Returns:
            Parsed synthesis dict.
        """
        json_text = text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Opus response as JSON, using defaults")
            parsed = {}

        bull = parsed.get("bull_case", {})
        bear = parsed.get("bear_case", {})
        rr = parsed.get("risk_reward", {})

        return {
            "bull_case": {
                "factors": bull.get("factors", []),
                "evidence": bull.get("evidence", []),
            },
            "bear_case": {
                "factors": bear.get("factors", []),
                "evidence": bear.get("evidence", []),
            },
            "verdict": parsed.get("verdict", "NEUTRAL"),
            "reasoning": parsed.get("reasoning", "Insufficient data for synthesis."),
            "risk_reward": {
                "ratio": float(rr.get("ratio", 0.0)),
                "upside_target": rr.get("upside_target", "N/A"),
                "downside_risk": rr.get("downside_risk", "N/A"),
                "explanation": rr.get("explanation", ""),
            },
            "confidence_explanation": parsed.get(
                "confidence_explanation",
                "Evidence quality could not be assessed.",
            ),
            "key_levels": parsed.get("key_levels", {"support": [], "resistance": []}),
            "catalysts_to_watch": parsed.get("catalysts_to_watch", []),
            "action_items": parsed.get("action_items", []),
        }
