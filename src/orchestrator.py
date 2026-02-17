"""Orchestrator — Coordinates the multi-agent analysis pipeline.

Routes tasks to appropriate Claude models based on tier selection:
  - Lite:     Technical + News (Haiku only)
  - Standard: Technical + News + SEC + Opus synthesis
  - Premium:  Standard + extended thinking

Uses Evidence Scorecard + Checklist Method (NO fake percentages).
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from src.agents.fundamental_agent import FundamentalAgent
from src.agents.news_agent import NewsAgent
from src.agents.synthesis_agent import SynthesisAgent
from src.analyzers.gap_analyzer import detect_gaps, summarize_gaps
from src.analyzers.sr_calculator import calculate_levels, summarize_levels
from src.analyzers.supply_demand import identify_zones, summarize_zones
from src.parsers.csv_parser import ParsedData, load_csv
from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger
from src.utils.tier_config import get_tier_config

logger = get_logger("orchestrator")


class TradingAnalysisOrchestrator:
    """Main orchestrator for the trading analysis pipeline.

    Coordinates technical analyzers, news agent, fundamental agent,
    and synthesis agent into a single end-to-end analysis.

    Args:
        tier: Analysis tier (lite, standard, premium).
        api_key: Anthropic API key. If None, reads from env.
        budget: Budget override in USD. If None, uses tier default.
        cost_log_path: Path for cost persistence. If None, in-memory only.
    """

    def __init__(
        self,
        tier: str = "standard",
        api_key: Optional[str] = None,
        budget: Optional[float] = None,
        cost_log_path: Optional[str] = None,
    ):
        self.tier_name = tier.lower()
        self.tier_config = get_tier_config(self.tier_name)
        self.api_key = api_key

        effective_budget = budget or self.tier_config["max_cost"]
        self.cost_tracker = CostTracker(
            budget=effective_budget,
            log_path=Path(cost_log_path) if cost_log_path else None,
        )

        # Initialize agents based on tier
        self._news_agent: Optional[NewsAgent] = None
        self._fundamental_agent: Optional[FundamentalAgent] = None
        self._synthesis_agent: Optional[SynthesisAgent] = None

        if self.tier_config["include_news"]:
            self._news_agent = NewsAgent(
                api_key=api_key, cost_tracker=self.cost_tracker
            )

        if self.tier_config["include_sec"]:
            self._fundamental_agent = FundamentalAgent(
                api_key=api_key, cost_tracker=self.cost_tracker
            )

        if self.tier_config["include_synthesis"]:
            self._synthesis_agent = SynthesisAgent(
                api_key=api_key, cost_tracker=self.cost_tracker
            )

    def analyze(
        self,
        symbol: str,
        csv_file: str,
        min_gap_pct: float = 2.0,
        news_lookback_days: int = 7,
    ) -> dict:
        """Execute the full analysis pipeline.

        Pipeline:
          1. Parse CSV data
          2. Run technical analysis (gaps, S/R, zones)
          3. Fetch and analyze news (if tier includes it)
          4. Fetch and analyze SEC filings (if tier includes it)
          5. Synthesize with Opus (if tier includes it)

        Args:
            symbol: Stock ticker symbol (e.g., "WHR").
            csv_file: Path to TradingView CSV file.
            min_gap_pct: Minimum gap size percentage for gap detection.
            news_lookback_days: Days to look back for news.

        Returns:
            Complete analysis dict with all components and cost tracking.
        """
        start_time = time.time()

        logger.info(
            f"Starting {self.tier_name} analysis for {symbol} "
            f"(budget: ${self.tier_config['max_cost']:.2f})"
        )

        result: dict = {
            "metadata": {
                "symbol": symbol,
                "tier": self.tier_name,
                "tier_label": self.tier_config["label"],
                "csv_file": str(csv_file),
            },
            "technical": {},
            "news": {},
            "fundamental": {},
            "synthesis": {},
            "errors": [],
            "cost_summary": {},
        }

        # Step 1: Parse CSV
        parsed = self._step_parse_csv(csv_file, result)
        if parsed is None:
            result["cost_summary"] = self._build_cost_summary(start_time)
            return result

        # Step 2: Technical analysis (always runs, no API cost)
        self._step_technical_analysis(parsed, min_gap_pct, result)

        # Steps 3+4: News + Fundamental run in PARALLEL (independent)
        self._run_parallel_agents(symbol, news_lookback_days, result)

        # Step 5: Synthesis runs AFTER both complete (needs their results)
        if self._synthesis_agent:
            self._step_synthesis(symbol, result)

        # Final: Cost summary
        result["cost_summary"] = self._build_cost_summary(start_time)

        logger.info(
            f"Analysis complete for {symbol}: "
            f"tier={self.tier_name}, "
            f"cost=${self.cost_tracker.get_total_cost():.4f}, "
            f"time={result['cost_summary']['execution_time_ms']}ms"
        )

        return result

    def analyze_from_parsed(
        self,
        symbol: str,
        parsed: ParsedData,
        min_gap_pct: float = 2.0,
        news_lookback_days: int = 7,
        filing_period: str = "annual",
    ) -> dict:
        """Run analysis from an already-parsed CSV (for API endpoint use).

        Args:
            symbol: Stock ticker symbol.
            parsed: Pre-parsed CSV data.
            min_gap_pct: Minimum gap size percentage.
            news_lookback_days: Days to look back for news.
            filing_period: "annual" or "quarterly" for SEC filings.

        Returns:
            Complete analysis dict.
        """
        start_time = time.time()
        timings: dict[str, float] = {}

        logger.info(
            f"Starting {self.tier_name} analysis for {symbol} (pre-parsed)"
        )

        result: dict = {
            "metadata": {
                "symbol": symbol,
                "tier": self.tier_name,
                "tier_label": self.tier_config["label"],
                "bars": parsed.bar_count,
                "timeframe": parsed.timeframe,
                "date_range": list(parsed.date_range),
            },
            "technical": {},
            "news": {},
            "fundamental": {},
            "synthesis": {},
            "errors": [],
            "cost_summary": {},
        }

        t = time.time()
        self._step_technical_analysis(parsed, min_gap_pct, result)
        timings["technical_s"] = round(time.time() - t, 2)
        logger.info(f"TIMING technical: {timings['technical_s']}s")

        # News + Fundamental run in PARALLEL (independent API calls)
        t = time.time()
        self._run_parallel_agents(
            symbol, news_lookback_days, result, filing_period
        )
        parallel_elapsed = round(time.time() - t, 2)
        timings["parallel_news_fundamental_s"] = parallel_elapsed
        logger.info(f"TIMING parallel news+fundamental: {parallel_elapsed}s")

        # Synthesis runs AFTER both complete (needs their results)
        if self._synthesis_agent:
            t = time.time()
            self._step_synthesis(symbol, result)
            timings["synthesis_s"] = round(time.time() - t, 2)
            logger.info(f"TIMING synthesis: {timings['synthesis_s']}s")

        result["cost_summary"] = self._build_cost_summary(start_time)
        result["cost_summary"]["timings"] = timings

        total = round(time.time() - start_time, 2)
        logger.info(
            f"TIMING TOTAL for {symbol} ({self.tier_name}): {total}s | "
            f"breakdown: {timings}"
        )

        return result

    # ── Pipeline steps ────────────────────────────────────────

    def _step_parse_csv(self, csv_file: str, result: dict) -> Optional[ParsedData]:
        """Step 1: Parse CSV file.

        Args:
            csv_file: Path to the CSV file.
            result: Result dict to update.

        Returns:
            ParsedData or None on failure.
        """
        logger.info(f"Step 1: Parsing CSV from {csv_file}")
        try:
            parsed = load_csv(csv_file)
            result["metadata"].update({
                "bars": parsed.bar_count,
                "timeframe": parsed.timeframe,
                "date_range": list(parsed.date_range),
                "indicators": parsed.indicators,
                "quality_score": round(parsed.quality.score, 3),
            })
            logger.info(
                f"Parsed {parsed.bar_count} bars, "
                f"timeframe={parsed.timeframe}, "
                f"quality={parsed.quality.score:.2f}"
            )
            return parsed
        except Exception as e:
            error_msg = f"CSV parse failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
            return None

    def _step_technical_analysis(
        self, parsed: ParsedData, min_gap_pct: float, result: dict
    ) -> None:
        """Step 2: Run technical analysis (no API cost).

        Args:
            parsed: Parsed CSV data.
            min_gap_pct: Minimum gap percentage.
            result: Result dict to update.
        """
        logger.info("Step 2: Running technical analysis")
        try:
            df = parsed.df
            current_price = float(df["close"].iloc[-1])

            gaps = detect_gaps(df, min_gap_pct=min_gap_pct)
            levels = calculate_levels(df, current_price=current_price)
            zones = identify_zones(df)

            result["technical"] = {
                "current_price": round(current_price, 2),
                "gaps": summarize_gaps(gaps),
                "support_resistance": summarize_levels(levels, current_price),
                "supply_demand": summarize_zones(zones, current_price),
            }
            # Sanitize numpy types
            result["technical"] = _sanitize_numpy(result["technical"])

            logger.info(
                f"Technical: {len(gaps)} gaps, {len(levels)} levels, "
                f"{len(zones)} zones"
            )
        except Exception as e:
            error_msg = f"Technical analysis failed: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

    def _step_news_analysis(
        self, symbol: str, lookback_days: int, result: dict
    ) -> None:
        """Step 3: News analysis via Haiku.

        Args:
            symbol: Stock ticker symbol.
            lookback_days: Days to look back.
            result: Result dict to update.
        """
        logger.info(f"Step 3: Analyzing news for {symbol}")
        try:
            news = self._news_agent.analyze(  # type: ignore[union-attr]
                symbol=symbol, lookback_days=lookback_days
            )
            result["news"] = news
            logger.info(
                f"News: sentiment={news.get('sentiment_score', 'N/A')}, "
                f"articles={news.get('article_count', 0)}, "
                f"cost=${news.get('cost', 0):.4f}"
            )
        except Exception as e:
            error_msg = f"News analysis failed: {e}"
            logger.warning(error_msg)
            result["errors"].append(error_msg)

    def _step_fundamental_analysis(
        self, symbol: str, result: dict, filing_period: str = "annual"
    ) -> None:
        """Step 4: Fundamental analysis via Sonnet.

        Args:
            symbol: Stock ticker symbol.
            result: Result dict to update.
            filing_period: "annual" or "quarterly".
        """
        logger.info(f"Step 4: Analyzing SEC filings for {symbol} ({filing_period})")
        try:
            fundamental = self._fundamental_agent.analyze(  # type: ignore[union-attr]
                symbol=symbol, filing_period=filing_period
            )
            result["fundamental"] = fundamental
            logger.info(
                f"Fundamental: grade={fundamental.get('financial_health', {}).get('overall_grade', 'N/A')}, "
                f"cost=${fundamental.get('cost', 0):.4f}"
            )
        except Exception as e:
            error_msg = f"Fundamental analysis failed: {e}"
            logger.warning(error_msg)
            result["errors"].append(error_msg)

    def _step_synthesis(self, symbol: str, result: dict) -> None:
        """Step 5: Opus synthesis.

        Args:
            symbol: Stock ticker symbol.
            result: Result dict to update.
        """
        logger.info(f"Step 5: Synthesizing analysis for {symbol}")
        try:
            synthesis = self._synthesis_agent.synthesize(  # type: ignore[union-attr]
                symbol=symbol,
                technical_data=result.get("technical") or None,
                news_data=result.get("news") or None,
                fundamental_data=result.get("fundamental") or None,
            )
            result["synthesis"] = synthesis
            logger.info(
                f"Synthesis: verdict={synthesis.get('verdict', 'N/A')}, "
                f"cost=${synthesis.get('cost', 0):.4f}"
            )
        except Exception as e:
            error_msg = f"Synthesis failed: {e}"
            logger.warning(error_msg)
            result["errors"].append(error_msg)

    def _run_parallel_agents(
        self,
        symbol: str,
        news_lookback_days: int,
        result: dict,
        filing_period: str = "annual",
    ) -> None:
        """Run news and fundamental agents in parallel using threads.

        Each agent writes to a separate key in the result dict, so
        concurrent access is safe. Exceptions are caught per-future
        and logged to result["errors"].

        Args:
            symbol: Stock ticker symbol.
            news_lookback_days: Days to look back for news.
            result: Result dict to update (thread-safe: separate keys).
            filing_period: "annual" or "quarterly" for SEC filings.
        """
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            if self._news_agent:
                futures[executor.submit(
                    self._step_news_analysis, symbol, news_lookback_days, result
                )] = "news"
            if self._fundamental_agent:
                futures[executor.submit(
                    self._step_fundamental_analysis, symbol, result, filing_period
                )] = "fundamental"

            for future in as_completed(futures):
                name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Parallel {name} failed: {e}")
                    result["errors"].append(f"{name} analysis failed: {e}")

    # ── Helpers ───────────────────────────────────────────────

    def _build_cost_summary(self, start_time: float) -> dict:
        """Build the cost summary section of the result.

        Args:
            start_time: Pipeline start timestamp from time.time().

        Returns:
            Cost summary dict.
        """
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "total_cost": round(self.cost_tracker.get_total_cost(), 6),
            "breakdown": self.cost_tracker.get_breakdown(),
            "budget": self.cost_tracker.budget,
            "budget_remaining": round(
                (self.cost_tracker.budget or 0) - self.cost_tracker.get_total_cost(), 6
            ),
            "execution_time_ms": elapsed_ms,
            "total_calls": len(self.cost_tracker.calls),
        }


    def generate_report(
        self,
        result: dict,
        format: str = "markdown",
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a formatted report from analysis results.

        Args:
            result: Complete analysis result dict from analyze().
            format: Output format — "markdown", "json", or "html".
            output_path: Optional file path to save the report.

        Returns:
            Report content as a string.

        Raises:
            ValueError: If format is not recognized.
        """
        format_lower = format.lower()

        if format_lower == "markdown":
            from src.outputs.markdown_generator import generate_markdown
            content = generate_markdown(result)
        elif format_lower == "json":
            from src.outputs.json_generator import generate_json
            content = generate_json(result)
        elif format_lower == "html":
            from src.outputs.html_generator import generate_html
            content = generate_html(result)
        else:
            raise ValueError(
                f"Unknown format '{format}'. Choose from: markdown, json, html"
            )

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info(f"Report saved to {output_path}")

        return content


def _sanitize_numpy(obj):
    """Recursively convert numpy types to native Python for JSON serialization."""
    try:
        import numpy as np

        if isinstance(obj, dict):
            return {k: _sanitize_numpy(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize_numpy(v) for v in obj]
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    return obj
