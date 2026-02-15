"""HTML report generator for trading analysis results.

Generates a standalone HTML file with:
  - Embedded CSS (no external dependencies)
  - Dark/light theme toggle
  - Collapsible sections
  - Responsive layout
  - Verdict badge with color coding

Uses Evidence Scorecard + Checklist Method (NO fake percentages).
"""

import html
import json
from datetime import datetime
from typing import Optional


class HTMLGenerator:
    """Generate standalone HTML reports from analysis results.

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
        """Generate the full standalone HTML report.

        Returns:
            Complete HTML document as a string.
        """
        symbol = _esc(self.metadata.get("symbol", "UNKNOWN"))
        return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trading Analysis: {symbol}</title>
{self._css()}
</head>
<body>
<div class="container">
{self._header_html()}
{self._metadata_html()}
{self._technical_html()}
{self._news_html()}
{self._fundamental_html()}
{self._synthesis_html()}
{self._cost_html()}
{self._errors_html()}
{self._footer_html()}
</div>
{self._javascript()}
</body>
</html>"""

    def _css(self) -> str:
        """Embedded CSS with dark/light themes."""
        return """<style>
:root {
  --bg: #1a1a2e;
  --surface: #16213e;
  --card: #0f3460;
  --text: #e0e0e0;
  --text-secondary: #a0a0b0;
  --accent: #e94560;
  --accent-green: #4ade80;
  --accent-yellow: #fbbf24;
  --border: #2a2a4a;
}
[data-theme="light"] {
  --bg: #f5f5f5;
  --surface: #ffffff;
  --card: #f0f4f8;
  --text: #1a1a2e;
  --text-secondary: #555;
  --accent: #e94560;
  --accent-green: #16a34a;
  --accent-yellow: #d97706;
  --border: #ddd;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
.container { max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }
header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;
}
header h1 { font-size: 1.8rem; }
.theme-toggle {
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text); padding: 0.5rem 1rem; border-radius: 6px;
  cursor: pointer; font-size: 0.9rem;
}
.badge {
  display: inline-block; padding: 0.3rem 0.8rem; border-radius: 4px;
  font-weight: bold; font-size: 0.85rem; text-transform: uppercase;
}
.badge-bull { background: #065f46; color: #a7f3d0; }
.badge-bear { background: #7f1d1d; color: #fecaca; }
.badge-neutral { background: #78350f; color: #fef3c7; }
[data-theme="light"] .badge-bull { background: #d1fae5; color: #065f46; }
[data-theme="light"] .badge-bear { background: #fee2e2; color: #991b1b; }
[data-theme="light"] .badge-neutral { background: #fef3c7; color: #78350f; }
.section {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 1.5rem; overflow: hidden;
}
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1rem 1.5rem; cursor: pointer; user-select: none;
}
.section-header:hover { background: var(--card); }
.section-header h2 { font-size: 1.2rem; }
.section-toggle { font-size: 1.2rem; transition: transform 0.2s; }
.section-toggle.collapsed { transform: rotate(-90deg); }
.section-body { padding: 0 1.5rem 1.5rem; }
.section-body.hidden { display: none; }
table {
  width: 100%; border-collapse: collapse; margin: 0.5rem 0;
  font-size: 0.9rem;
}
th, td {
  padding: 0.5rem 0.8rem; text-align: left;
  border-bottom: 1px solid var(--border);
}
th { color: var(--text-secondary); font-weight: 600; }
.tag {
  display: inline-block; padding: 0.15rem 0.5rem; margin: 0.15rem;
  background: var(--card); border-radius: 3px; font-size: 0.8rem;
}
.metric { margin-bottom: 0.8rem; }
.metric-label { color: var(--text-secondary); font-size: 0.85rem; }
.metric-value { font-size: 1.1rem; font-weight: bold; }
.case-box {
  background: var(--card); border-radius: 6px;
  padding: 1rem; margin: 0.5rem 0;
}
.case-box h4 { margin-bottom: 0.5rem; }
.case-box ul { padding-left: 1.2rem; }
.case-box li { margin-bottom: 0.3rem; }
.evidence { color: var(--text-secondary); font-size: 0.85rem; margin-left: 0.5rem; }
footer {
  text-align: center; color: var(--text-secondary);
  font-size: 0.8rem; margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid var(--border);
}
@media (max-width: 600px) {
  .container { padding: 1rem 0.5rem; }
  header h1 { font-size: 1.4rem; }
  table { font-size: 0.8rem; }
  th, td { padding: 0.3rem 0.5rem; }
}
</style>"""

    def _header_html(self) -> str:
        """HTML header with symbol and theme toggle."""
        symbol = _esc(self.metadata.get("symbol", "UNKNOWN"))
        tier = _esc(self.metadata.get("tier_label", self.metadata.get("tier", "")))
        verdict = self.synthesis.get("verdict", "")
        badge_class = _verdict_badge_class(verdict)
        verdict_display = _esc(verdict.replace("_", " ").title()) if verdict else ""

        verdict_html = ""
        if verdict_display:
            verdict_html = f' <span class="badge {badge_class}">{verdict_display}</span>'

        return f"""<header>
<div>
<h1>{symbol} Analysis{verdict_html}</h1>
<span style="color: var(--text-secondary);">{tier} | {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
</div>
<button class="theme-toggle" onclick="toggleTheme()">Toggle Theme</button>
</header>"""

    def _metadata_html(self) -> str:
        """Data summary section."""
        bars = self.metadata.get("bars", "N/A")
        tf = _esc(str(self.metadata.get("timeframe", "N/A")))
        dr = self.metadata.get("date_range", [])
        dr_str = f"{dr[0]} to {dr[1]}" if len(dr) >= 2 else "N/A"

        return self._section("Data Summary", f"""
<table>
<tr><th>Bars</th><td>{bars}</td></tr>
<tr><th>Timeframe</th><td>{tf}</td></tr>
<tr><th>Date Range</th><td>{dr_str}</td></tr>
</table>""")

    def _technical_html(self) -> str:
        """Technical analysis section."""
        if not self.technical:
            return ""

        parts = []
        price = self.technical.get("current_price")
        if price:
            parts.append(f'<div class="metric"><span class="metric-label">Current Price</span><br>'
                         f'<span class="metric-value">${price:,.2f}</span></div>')

        # Gaps table
        gaps = self.technical.get("gaps", {})
        total_gaps = gaps.get("total", 0)
        unfilled = gaps.get("unfilled", 0)
        parts.append(f'<div class="metric"><span class="metric-label">Gaps</span><br>'
                     f'<span class="metric-value">{total_gaps} total, {unfilled} unfilled</span></div>')

        gap_list = gaps.get("gaps", [])
        if gap_list:
            rows = ""
            for g in gap_list[:10]:
                date = _esc(str(g.get("date", "")))
                gtype = _esc(str(g.get("type", "")))
                size = g.get("gap_pct", 0)
                filled = "Yes" if g.get("filled") else "No"
                rows += (f"<tr><td>{date}</td><td>{gtype}</td>"
                         f"<td>{size:.1f}%</td><td>{filled}</td></tr>")
            parts.append(f"""<table>
<tr><th>Date</th><th>Type</th><th>Size</th><th>Filled</th></tr>
{rows}</table>""")

        # S/R levels
        sr = self.technical.get("support_resistance", {})
        supports = sr.get("supports", [])
        resistances = sr.get("resistances", [])
        if supports or resistances:
            sr_rows = ""
            for s in supports[:5]:
                level = s.get("level", s.get("price", 0))
                strength = _esc(str(s.get("strength", "")))
                sr_rows += f'<tr><td>Support</td><td>${level:,.2f}</td><td>{strength}</td></tr>'
            for r in resistances[:5]:
                level = r.get("level", r.get("price", 0))
                strength = _esc(str(r.get("strength", "")))
                sr_rows += f'<tr><td>Resistance</td><td>${level:,.2f}</td><td>{strength}</td></tr>'
            parts.append(f"""<h4>Support & Resistance</h4>
<table><tr><th>Type</th><th>Level</th><th>Strength</th></tr>{sr_rows}</table>""")

        # Zones
        sd = self.technical.get("supply_demand", {})
        zones = sd.get("zones", [])
        if zones:
            zone_rows = ""
            for z in zones[:8]:
                ztype = _esc(str(z.get("type", "")).title())
                low = z.get("low", 0)
                high = z.get("high", 0)
                strength = _esc(str(z.get("strength", "")))
                zone_rows += (f"<tr><td>{ztype}</td><td>${low:,.2f} - ${high:,.2f}</td>"
                              f"<td>{strength}</td></tr>")
            parts.append(f"""<h4>Supply/Demand Zones</h4>
<table><tr><th>Type</th><th>Range</th><th>Strength</th></tr>{zone_rows}</table>""")

        return self._section("Technical Analysis", "\n".join(parts))

    def _news_html(self) -> str:
        """News section."""
        if not self.news:
            return ""

        parts = []
        score = self.news.get("sentiment_score")
        label = _esc(str(self.news.get("sentiment_label", "")))
        if score is not None:
            parts.append(f'<div class="metric"><span class="metric-label">Sentiment</span><br>'
                         f'<span class="metric-value">{score}/10 ({label})</span></div>')

        articles = self.news.get("article_count", 0)
        parts.append(f'<div class="metric"><span class="metric-label">Articles</span><br>'
                     f'<span class="metric-value">{articles}</span></div>')

        catalysts = self.news.get("catalysts", [])
        if catalysts:
            tags = " ".join(f'<span class="tag">{_esc(c)}</span>' for c in catalysts)
            parts.append(f"<h4>Catalysts</h4>{tags}")

        themes = self.news.get("key_themes", [])
        if themes:
            tags = " ".join(f'<span class="tag">{_esc(t)}</span>' for t in themes)
            parts.append(f"<h4>Key Themes</h4>{tags}")

        summary = self.news.get("summary", "")
        if summary:
            parts.append(f"<h4>Summary</h4><p>{_esc(summary)}</p>")

        return self._section("News & Sentiment", "\n".join(parts))

    def _fundamental_html(self) -> str:
        """Fundamental analysis section."""
        if not self.fundamental:
            return ""

        parts = []
        fh = self.fundamental.get("financial_health", {})
        grade = _esc(str(fh.get("overall_grade", "N/A")))
        parts.append(f'<div class="metric"><span class="metric-label">Overall Grade</span><br>'
                     f'<span class="metric-value">{grade}</span></div>')

        # Health metrics table
        metrics_rows = ""
        for key in ("revenue_trend", "margin_trend", "debt_level", "cash_flow"):
            val = fh.get(key)
            if val:
                label = key.replace("_", " ").title()
                metrics_rows += f"<tr><th>{label}</th><td>{_esc(str(val))}</td></tr>"
        if metrics_rows:
            parts.append(f"<table>{metrics_rows}</table>")

        risks = self.fundamental.get("key_risks", [])
        if risks:
            items = "".join(f"<li>{_esc(r)}</li>" for r in risks)
            parts.append(f'<div class="case-box"><h4>Key Risks</h4><ul>{items}</ul></div>')

        opps = self.fundamental.get("opportunities", [])
        if opps:
            items = "".join(f"<li>{_esc(o)}</li>" for o in opps)
            parts.append(f'<div class="case-box"><h4>Opportunities</h4><ul>{items}</ul></div>')

        commentary = self.fundamental.get("management_commentary", "")
        if commentary:
            parts.append(f"<h4>Management Commentary</h4><p>{_esc(commentary)}</p>")

        return self._section("Fundamental Analysis", "\n".join(parts))

    def _synthesis_html(self) -> str:
        """Synthesis section with verdict badge."""
        if not self.synthesis:
            return ""

        parts = []

        verdict = self.synthesis.get("verdict", "N/A")
        badge_class = _verdict_badge_class(verdict)
        verdict_display = _esc(verdict.replace("_", " ").title())
        parts.append(f'<div class="metric"><span class="metric-label">Verdict</span><br>'
                     f'<span class="badge {badge_class}" style="font-size:1.1rem;">'
                     f'{verdict_display}</span></div>')

        reasoning = self.synthesis.get("reasoning", "")
        if reasoning:
            parts.append(f"<p>{_esc(reasoning)}</p>")

        # Bull case
        bull = self.synthesis.get("bull_case", {})
        if bull:
            factors = bull.get("factors", [])
            evidence = bull.get("evidence", [])
            items = ""
            for i, f in enumerate(factors):
                ev = f'<span class="evidence">({_esc(evidence[i])})</span>' if i < len(evidence) else ""
                items += f"<li>{_esc(f)} {ev}</li>"
            parts.append(f'<div class="case-box"><h4>Bull Case</h4><ul>{items}</ul></div>')

        # Bear case
        bear = self.synthesis.get("bear_case", {})
        if bear:
            factors = bear.get("factors", [])
            evidence = bear.get("evidence", [])
            items = ""
            for i, f in enumerate(factors):
                ev = f'<span class="evidence">({_esc(evidence[i])})</span>' if i < len(evidence) else ""
                items += f"<li>{_esc(f)} {ev}</li>"
            parts.append(f'<div class="case-box"><h4>Bear Case</h4><ul>{items}</ul></div>')

        # Risk/Reward
        rr = self.synthesis.get("risk_reward", {})
        if rr:
            rr_items = ""
            if rr.get("ratio"):
                rr_items += f"<tr><th>Ratio</th><td>{_esc(str(rr['ratio']))}</td></tr>"
            if rr.get("upside_target"):
                rr_items += f"<tr><th>Upside Target</th><td>{_esc(str(rr['upside_target']))}</td></tr>"
            if rr.get("downside_risk"):
                rr_items += f"<tr><th>Downside Risk</th><td>{_esc(str(rr['downside_risk']))}</td></tr>"
            if rr_items:
                parts.append(f"<h4>Risk/Reward</h4><table>{rr_items}</table>")

        conf = self.synthesis.get("confidence_explanation", "")
        if conf:
            parts.append(f"<h4>Confidence</h4><p>{_esc(conf)}</p>")

        return self._section("Synthesis & Verdict", "\n".join(parts))

    def _cost_html(self) -> str:
        """Cost summary section."""
        if not self.cost_summary:
            return ""

        total = self.cost_summary.get("total_cost", 0)
        budget = self.cost_summary.get("budget", 0)
        calls = self.cost_summary.get("total_calls", 0)
        time_ms = self.cost_summary.get("execution_time_ms", 0)
        pct = (total / budget * 100) if budget else 0

        parts = [f"""<table>
<tr><th>Total Cost</th><td>${total:.4f}</td></tr>
<tr><th>Budget</th><td>${budget:.2f}</td></tr>
<tr><th>Budget Used</th><td>{pct:.1f}%</td></tr>
<tr><th>API Calls</th><td>{calls}</td></tr>
<tr><th>Execution Time</th><td>{time_ms}ms</td></tr>
</table>"""]

        breakdown = self.cost_summary.get("breakdown", {})
        if breakdown:
            rows = ""
            for model, info in sorted(breakdown.items()):
                rows += (f"<tr><td>{_esc(model)}</td><td>{info['calls']}</td>"
                         f"<td>{info['input_tokens']:,}</td>"
                         f"<td>{info['output_tokens']:,}</td>"
                         f"<td>${info['cost']:.4f}</td></tr>")
            parts.append(f"""<h4>Per-Model Breakdown</h4>
<table>
<tr><th>Model</th><th>Calls</th><th>Input</th><th>Output</th><th>Cost</th></tr>
{rows}</table>""")

        return self._section("Cost Summary", "\n".join(parts))

    def _errors_html(self) -> str:
        """Errors/warnings section."""
        if not self.errors:
            return ""
        items = "".join(f"<li>{_esc(e)}</li>" for e in self.errors)
        return self._section("Warnings", f"<ul>{items}</ul>")

    def _footer_html(self) -> str:
        """Footer."""
        return ('<footer>Generated by Trading Analyzer. '
                'Uses Evidence Scorecard method &mdash; no fake percentages.</footer>')

    def _section(self, title: str, body: str) -> str:
        """Wrap content in a collapsible section."""
        return f"""<div class="section">
<div class="section-header" onclick="toggleSection(this)">
<h2>{_esc(title)}</h2>
<span class="section-toggle">&#9660;</span>
</div>
<div class="section-body">
{body}
</div>
</div>"""

    def _javascript(self) -> str:
        """Embedded JS for theme toggle and collapsible sections."""
        return """<script>
function toggleTheme() {
  var el = document.documentElement;
  el.dataset.theme = el.dataset.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', el.dataset.theme);
}
function toggleSection(header) {
  var body = header.nextElementSibling;
  var toggle = header.querySelector('.section-toggle');
  body.classList.toggle('hidden');
  toggle.classList.toggle('collapsed');
}
(function() {
  var saved = localStorage.getItem('theme');
  if (saved) document.documentElement.dataset.theme = saved;
})();
</script>"""


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text))


def _verdict_badge_class(verdict: str) -> str:
    """Map verdict to CSS badge class."""
    v = verdict.upper()
    if "BULL" in v:
        return "badge-bull"
    if "BEAR" in v:
        return "badge-bear"
    return "badge-neutral"


def generate_html(result: dict) -> str:
    """Convenience function to generate an HTML report.

    Args:
        result: Complete analysis result dict.

    Returns:
        Complete HTML document string.
    """
    return HTMLGenerator(result).generate()
