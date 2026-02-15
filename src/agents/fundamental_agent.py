"""Fundamental analysis agent powered by Claude Sonnet.

Fetches SEC filings (10-K, 10-Q) for a stock symbol and uses Sonnet to
extract financial health metrics, key risks, opportunities, and management
commentary.

Cost target: <$0.80 per analysis.
"""

import json
from typing import Optional

from src.agents.model_wrappers import SonnetWrapper, get_wrapper
from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger
from src.utils.sec_fetcher import fetch_latest_filings, fetch_filing_by_type

logger = get_logger("fundamental_agent")

FUNDAMENTAL_SYSTEM_PROMPT = """\
You are an expert fundamental analyst specializing in SEC filings.
You analyze 10-K and 10-Q filings to extract actionable financial insights.

You MUST respond with valid JSON only — no markdown, no explanation, no code fences.

Your response format:
{
  "financial_health": {
    "revenue_trend": "<growing|stable|declining>",
    "revenue_latest": "<latest revenue figure with unit, e.g. '$5.2B'>",
    "profit_margin_trend": "<expanding|stable|compressing>",
    "debt_level": "<low|moderate|high|critical>",
    "cash_position": "<strong|adequate|weak>",
    "overall_grade": "<A|B|C|D|F>"
  },
  "key_risks": [
    "<risk 1 — concise, specific, factual>",
    "<risk 2>",
    "<risk 3>"
  ],
  "opportunities": [
    "<opportunity 1 — concise, specific, factual>",
    "<opportunity 2>",
    "<opportunity 3>"
  ],
  "management_commentary": "<2-3 sentence summary of management's tone, outlook, and strategic direction from the filing>",
  "key_metrics": {
    "<metric_name>": "<value>",
    "<metric_name>": "<value>"
  },
  "competitive_position": "<1-2 sentences on market position and competitive moat>",
  "filing_quality": "<comprehensive|adequate|limited>"
}

Rules:
- Only state facts found in the filing. Do NOT fabricate numbers or metrics.
- If a metric is not available in the text, say "not disclosed" rather than guessing.
- key_risks and opportunities should each have 3-5 items.
- key_metrics should include whatever financial figures are explicitly stated (revenue, net income, EPS, etc.).
- Be objective and balanced — present both bullish and bearish facts.\
"""


class FundamentalAgent:
    """Sonnet-powered fundamental analysis agent.

    Fetches SEC filings and sends them to Sonnet for deep analysis
    of financial health, risks, and opportunities.

    Args:
        api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        cost_tracker: Optional CostTracker for budget management.
        max_filing_chars: Maximum characters of filing text to send to Sonnet.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        max_filing_chars: int = 80_000,
    ):
        self.sonnet = get_wrapper(
            "sonnet", api_key=api_key, cost_tracker=cost_tracker
        )
        self.cost_tracker = cost_tracker
        self.max_filing_chars = max_filing_chars

    def analyze(
        self,
        symbol: str,
        filing_type: str = "10-K",
    ) -> dict:
        """Analyze SEC filings for a stock symbol.

        Fetches the most recent filing of the specified type and sends
        it to Sonnet for analysis.

        Args:
            symbol: Stock ticker symbol (e.g., "WHR").
            filing_type: Filing type to analyze (default "10-K").

        Returns:
            Dict with keys: financial_health, key_risks, opportunities,
            management_commentary, key_metrics, competitive_position,
            filing_info, cost.
        """
        logger.info(f"Starting fundamental analysis for {symbol} ({filing_type})")

        # Step 1: Fetch the filing
        filing = fetch_filing_by_type(
            symbol=symbol,
            filing_type=filing_type,
            max_text_length=self.max_filing_chars,
        )

        if filing is None:
            logger.warning(f"No {filing_type} filing found for {symbol}")
            return self._empty_result(symbol, filing_type)

        if not filing.get("text_content"):
            logger.warning(f"Filing found but text content is empty for {symbol}")
            return self._empty_result(symbol, filing_type)

        logger.info(
            f"Retrieved {filing_type} for {symbol}: "
            f"{len(filing['text_content']):,} chars, dated {filing['date']}"
        )

        # Step 2: Build prompt
        prompt = self._build_prompt(symbol, filing)

        # Step 3: Send to Sonnet
        result = self.sonnet.call(
            prompt=prompt,
            system=FUNDAMENTAL_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.0,
            component="fundamental_agent",
        )

        # Step 4: Parse response
        analysis = self._parse_response(result["text"])
        analysis["symbol"] = symbol
        analysis["filing_info"] = {
            "type": filing["filing_type"],
            "date": filing["date"],
            "url": filing["url"],
            "accession_number": filing.get("accession_number", ""),
            "text_length": len(filing["text_content"]),
        }
        analysis["cost"] = result["cost"]
        analysis["input_tokens"] = result["input_tokens"]
        analysis["output_tokens"] = result["output_tokens"]

        logger.info(
            f"Fundamental analysis complete for {symbol}: "
            f"grade={analysis.get('financial_health', {}).get('overall_grade', 'N/A')}, "
            f"risks={len(analysis.get('key_risks', []))}, "
            f"cost=${result['cost']:.4f}"
        )

        return analysis

    def analyze_multiple(
        self,
        symbol: str,
        filing_types: Optional[list[str]] = None,
    ) -> dict:
        """Analyze multiple filing types and combine results.

        Args:
            symbol: Stock ticker symbol.
            filing_types: List of filing types (default: ["10-K", "10-Q"]).

        Returns:
            Combined analysis dict with per-filing results.
        """
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]

        results: dict = {
            "symbol": symbol,
            "filings_analyzed": [],
            "combined_risks": [],
            "combined_opportunities": [],
            "total_cost": 0.0,
        }

        for ft in filing_types:
            analysis = self.analyze(symbol, filing_type=ft)
            results["filings_analyzed"].append(analysis)
            results["combined_risks"].extend(analysis.get("key_risks", []))
            results["combined_opportunities"].extend(
                analysis.get("opportunities", [])
            )
            results["total_cost"] += analysis.get("cost", 0.0)

        # Deduplicate risks and opportunities
        results["combined_risks"] = list(dict.fromkeys(results["combined_risks"]))
        results["combined_opportunities"] = list(
            dict.fromkeys(results["combined_opportunities"])
        )

        return results

    def _build_prompt(self, symbol: str, filing: dict) -> str:
        """Build the analysis prompt from a filing.

        Args:
            symbol: Stock ticker symbol.
            filing: Filing dict from sec_fetcher.

        Returns:
            Formatted prompt string.
        """
        text = filing["text_content"]

        # Truncate if needed to fit within Sonnet's context
        if len(text) > self.max_filing_chars:
            text = text[: self.max_filing_chars]

        return (
            f"Analyze the following {filing['filing_type']} filing for "
            f"{symbol} (filed {filing['date']}).\n\n"
            f"--- FILING TEXT ---\n{text}\n--- END FILING ---\n\n"
            f"Extract the financial health, key risks, opportunities, and "
            f"management commentary for {symbol}."
        )

    def _parse_response(self, text: str) -> dict:
        """Parse Sonnet's JSON response into structured output.

        Args:
            text: Raw response text from Sonnet.

        Returns:
            Parsed analysis dict.
        """
        # Extract JSON from response (handle potential markdown fences)
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
            logger.warning("Failed to parse Sonnet response as JSON, using defaults")
            parsed = {}

        return {
            "financial_health": parsed.get("financial_health", {
                "revenue_trend": "unknown",
                "revenue_latest": "not disclosed",
                "profit_margin_trend": "unknown",
                "debt_level": "unknown",
                "cash_position": "unknown",
                "overall_grade": "N/A",
            }),
            "key_risks": parsed.get("key_risks", []),
            "opportunities": parsed.get("opportunities", []),
            "management_commentary": parsed.get(
                "management_commentary", "No analysis available."
            ),
            "key_metrics": parsed.get("key_metrics", {}),
            "competitive_position": parsed.get(
                "competitive_position", "Not assessed."
            ),
            "filing_quality": parsed.get("filing_quality", "unknown"),
        }

    def _empty_result(self, symbol: str, filing_type: str) -> dict:
        """Return empty result when no filing is available.

        Args:
            symbol: Stock ticker symbol.
            filing_type: The filing type that was requested.

        Returns:
            Empty analysis dict with default values.
        """
        return {
            "symbol": symbol,
            "financial_health": {
                "revenue_trend": "unknown",
                "revenue_latest": "not disclosed",
                "profit_margin_trend": "unknown",
                "debt_level": "unknown",
                "cash_position": "unknown",
                "overall_grade": "N/A",
            },
            "key_risks": [],
            "opportunities": [],
            "management_commentary": f"No {filing_type} filing found for {symbol}.",
            "key_metrics": {},
            "competitive_position": "Not assessed.",
            "filing_quality": "unknown",
            "filing_info": {
                "type": filing_type,
                "date": "",
                "url": "",
                "accession_number": "",
                "text_length": 0,
            },
            "cost": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
