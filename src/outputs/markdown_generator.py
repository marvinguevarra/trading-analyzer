"""Markdown report generator for trading analysis results.

Converts the orchestrator result dict into a clean, readable Markdown report.
Uses Evidence Scorecard + Checklist Method (NO fake percentages).
"""

from datetime import datetime
from typing import Optional


class MarkdownGenerator:
    """Generate Markdown reports from analysis results.

    Args:
        result: Complete analysis result dict from TradingAnalysisOrchestrator.
    """

    def __init__(self, result: dict):
        self.result = result
        self.metadata = result.get("metadata", {})
        self.technical = result.get("technical", {})
        self.news = result.get("news", {})
        self.fundamental = result.get("fundamental", {})
        self.synthesis = result.get("synthesis", {})
        self.cost_summary = result.get("cost_summary", {})
        self.errors = result.get("errors", [])

    def generate(self) -> str:
        """Generate the full Markdown report.

        Returns:
            Complete Markdown report as a string.
        """
        sections = [
            self._header(),
            self._metadata_section(),
            self._technical_section(),
            self._news_section(),
            self._fundamental_section(),
            self._synthesis_section(),
            self._cost_section(),
            self._errors_section(),
            self._footer(),
        ]
        return "\n".join(s for s in sections if s)

    def _header(self) -> str:
        """Generate report header."""
        symbol = self.metadata.get("symbol", "UNKNOWN")
        tier = self.metadata.get("tier_label", self.metadata.get("tier", ""))
        return (
            f"# Trading Analysis: {symbol}\n\n"
            f"**Tier:** {tier}  \n"
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
        )

    def _metadata_section(self) -> str:
        """Generate metadata section."""
        lines = ["## Data Summary\n"]
        bars = self.metadata.get("bars", "N/A")
        tf = self.metadata.get("timeframe", "N/A")
        dr = self.metadata.get("date_range", [])
        date_range_str = f"{dr[0]} to {dr[1]}" if len(dr) >= 2 else "N/A"

        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Bars | {bars} |")
        lines.append(f"| Timeframe | {tf} |")
        lines.append(f"| Date Range | {date_range_str} |")
        if "quality_score" in self.metadata:
            lines.append(f"| Quality Score | {self.metadata['quality_score']} |")
        lines.append("")
        return "\n".join(lines)

    def _technical_section(self) -> str:
        """Generate technical analysis section."""
        if not self.technical:
            return ""

        lines = ["## Technical Analysis\n"]

        # Current price
        price = self.technical.get("current_price")
        if price:
            lines.append(f"**Current Price:** ${price:,.2f}\n")

        # Gaps
        gaps = self.technical.get("gaps", {})
        total_gaps = gaps.get("total", 0)
        unfilled = gaps.get("unfilled", 0)
        lines.append(f"### Gaps\n")
        lines.append(f"- **Total gaps detected:** {total_gaps}")
        lines.append(f"- **Unfilled gaps:** {unfilled}")

        gap_list = gaps.get("gaps", [])
        if gap_list:
            lines.append(f"\n| Date | Type | Size | Gap Range | Filled |")
            lines.append(f"|------|------|------|-----------|--------|")
            for g in gap_list[:15]:
                date = g.get("date", "")
                gtype = g.get("type", "")
                size = g.get("gap_pct", 0)
                low = g.get("gap_low", 0)
                high = g.get("gap_high", 0)
                filled = "Yes" if g.get("filled") else "No"
                lines.append(
                    f"| {date} | {gtype} | {size:.1f}% | "
                    f"${low:,.2f} - ${high:,.2f} | {filled} |"
                )
        lines.append("")

        # Support/Resistance
        sr = self.technical.get("support_resistance", {})
        lines.append("### Support & Resistance\n")
        supports = sr.get("supports", [])
        resistances = sr.get("resistances", [])

        if supports:
            lines.append("**Support Levels:**")
            for s in supports[:5]:
                level = s.get("level", s.get("price", 0))
                strength = s.get("strength", "")
                distance = s.get("distance_pct", 0)
                lines.append(
                    f"- ${level:,.2f} (strength: {strength}, "
                    f"distance: {distance:+.1f}%)"
                )
            lines.append("")

        if resistances:
            lines.append("**Resistance Levels:**")
            for r in resistances[:5]:
                level = r.get("level", r.get("price", 0))
                strength = r.get("strength", "")
                distance = r.get("distance_pct", 0)
                lines.append(
                    f"- ${level:,.2f} (strength: {strength}, "
                    f"distance: {distance:+.1f}%)"
                )
            lines.append("")

        # Supply/Demand zones
        sd = self.technical.get("supply_demand", {})
        zones = sd.get("zones", [])
        if zones:
            lines.append("### Supply/Demand Zones\n")
            for z in zones[:10]:
                ztype = z.get("type", "")
                low = z.get("low", 0)
                high = z.get("high", 0)
                strength = z.get("strength", "")
                lines.append(
                    f"- **{ztype.title()}:** ${low:,.2f} - ${high:,.2f} "
                    f"(strength: {strength})"
                )
            lines.append("")

        return "\n".join(lines)

    def _news_section(self) -> str:
        """Generate news analysis section."""
        if not self.news:
            return ""

        lines = ["## News & Sentiment\n"]

        score = self.news.get("sentiment_score")
        label = self.news.get("sentiment_label", "")
        if score is not None:
            lines.append(f"**Sentiment Score:** {score}/10 ({label})\n")

        articles = self.news.get("article_count", 0)
        lines.append(f"**Articles Analyzed:** {articles}\n")

        # Catalysts
        catalysts = self.news.get("catalysts", [])
        if catalysts:
            lines.append("### Catalysts")
            for c in catalysts:
                lines.append(f"- {c}")
            lines.append("")

        # Key themes
        themes = self.news.get("key_themes", [])
        if themes:
            lines.append("### Key Themes")
            for t in themes:
                lines.append(f"- {t}")
            lines.append("")

        # Summary
        summary = self.news.get("summary", "")
        if summary:
            lines.append("### Summary\n")
            lines.append(f"{summary}\n")

        return "\n".join(lines)

    def _fundamental_section(self) -> str:
        """Generate fundamental analysis section."""
        if not self.fundamental:
            return ""

        lines = ["## Fundamental Analysis\n"]

        # Financial health
        fh = self.fundamental.get("financial_health", {})
        grade = fh.get("overall_grade", "N/A")
        lines.append(f"**Overall Grade:** {grade}\n")

        if fh.get("revenue_trend"):
            lines.append(f"- Revenue Trend: {fh['revenue_trend']}")
        if fh.get("profit_margin_trend"):
            lines.append(f"- Profit Margin Trend: {fh['profit_margin_trend']}")
        if fh.get("debt_level"):
            lines.append(f"- Debt Level: {fh['debt_level']}")
        if fh.get("cash_position"):
            lines.append(f"- Cash Position: {fh['cash_position']}")
        lines.append("")

        # Key risks
        risks = self.fundamental.get("key_risks", [])
        if risks:
            lines.append("### Key Risks")
            for r in risks:
                lines.append(f"- {r}")
            lines.append("")

        # Opportunities
        opps = self.fundamental.get("opportunities", [])
        if opps:
            lines.append("### Opportunities")
            for o in opps:
                lines.append(f"- {o}")
            lines.append("")

        # Management commentary
        commentary = self.fundamental.get("management_commentary", "")
        if commentary:
            lines.append("### Management Commentary\n")
            lines.append(f"{commentary}\n")

        return "\n".join(lines)

    def _synthesis_section(self) -> str:
        """Generate synthesis section (Opus analysis)."""
        if not self.synthesis:
            return ""

        lines = ["## Synthesis & Verdict\n"]

        verdict = self.synthesis.get("verdict", "N/A")
        verdict_display = verdict.replace("_", " ").title()
        lines.append(f"### Verdict: {verdict_display}\n")

        # Reasoning
        reasoning = self.synthesis.get("reasoning", "")
        if reasoning:
            lines.append(f"{reasoning}\n")

        # Bull case
        bull = self.synthesis.get("bull_case", {})
        if bull:
            lines.append("### Bull Case")
            factors = bull.get("factors", [])
            evidence = bull.get("evidence", [])
            for i, f in enumerate(factors):
                lines.append(f"- **{f}**")
                if i < len(evidence):
                    lines.append(f"  - Evidence: {evidence[i]}")
            lines.append("")

        # Bear case
        bear = self.synthesis.get("bear_case", {})
        if bear:
            lines.append("### Bear Case")
            factors = bear.get("factors", [])
            evidence = bear.get("evidence", [])
            for i, f in enumerate(factors):
                lines.append(f"- **{f}**")
                if i < len(evidence):
                    lines.append(f"  - Evidence: {evidence[i]}")
            lines.append("")

        # Risk/Reward
        rr = self.synthesis.get("risk_reward", {})
        if rr:
            lines.append("### Risk/Reward")
            if rr.get("ratio"):
                lines.append(f"- **Ratio:** {rr['ratio']}")
            if rr.get("upside_target"):
                lines.append(f"- **Upside Target:** {rr['upside_target']}")
            if rr.get("downside_risk"):
                lines.append(f"- **Downside Risk:** {rr['downside_risk']}")
            lines.append("")

        # Confidence
        conf = self.synthesis.get("confidence_explanation", "")
        if conf:
            lines.append("### Confidence Assessment\n")
            lines.append(f"{conf}\n")

        return "\n".join(lines)

    def _cost_section(self) -> str:
        """Generate cost tracking section."""
        if not self.cost_summary:
            return ""

        lines = ["## Cost Summary\n"]
        total = self.cost_summary.get("total_cost", 0)
        budget = self.cost_summary.get("budget", 0)
        calls = self.cost_summary.get("total_calls", 0)
        time_ms = self.cost_summary.get("execution_time_ms", 0)

        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Cost | ${total:.4f} |")
        lines.append(f"| Budget | ${budget:.2f} |")
        lines.append(f"| Budget Used | {(total / budget * 100) if budget else 0:.1f}% |")
        lines.append(f"| API Calls | {calls} |")
        lines.append(f"| Execution Time | {time_ms}ms |")
        lines.append("")

        # Breakdown
        breakdown = self.cost_summary.get("breakdown", {})
        if breakdown:
            lines.append("### Per-Model Breakdown\n")
            lines.append("| Model | Calls | Input Tokens | Output Tokens | Cost |")
            lines.append("|-------|-------|-------------|---------------|------|")
            for model, info in sorted(breakdown.items()):
                lines.append(
                    f"| {model} | {info['calls']} | "
                    f"{info['input_tokens']:,} | {info['output_tokens']:,} | "
                    f"${info['cost']:.4f} |"
                )
            lines.append("")

        return "\n".join(lines)

    def _errors_section(self) -> str:
        """Generate errors/warnings section."""
        if not self.errors:
            return ""

        lines = ["## Warnings\n"]
        for e in self.errors:
            lines.append(f"- {e}")
        lines.append("")
        return "\n".join(lines)

    def _footer(self) -> str:
        """Generate report footer."""
        return (
            "---\n\n"
            "*Generated by Trading Analyzer. "
            "Uses Evidence Scorecard method — no fake percentages.*\n"
        )


def generate_markdown(result: dict) -> str:
    """Convenience function to generate a Markdown report.

    Args:
        result: Complete analysis result dict.

    Returns:
        Markdown report string.
    """
    return MarkdownGenerator(result).generate()
