"""News analysis agent powered by Claude with web search.

Uses Claude's built-in web_search tool to find and analyze recent news
for a stock symbol in a single API call. Claude searches the web,
reads the articles, and returns structured sentiment analysis.

Cost: ~$0.01-0.03 per analysis (Haiku + web search).
"""

import json
import os
from typing import Optional

import anthropic

from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger

logger = get_logger("news_agent")

# Web search costs $10 per 1000 queries = $0.01 per search
WEB_SEARCH_COST = 0.01

NEWS_SYSTEM_PROMPT = """\
You are a financial news analyst. Search for the latest news about
the given stock symbol, then provide a structured analysis.

You MUST respond with valid JSON only — no markdown, no explanation,
no code fences.

Your response format:
{
  "sentiment_score": <float 1-10, where 1=very bearish, 5=neutral, 10=very bullish>,
  "sentiment_label": "<bearish|slightly_bearish|neutral|slightly_bullish|bullish>",
  "catalysts": ["<catalyst 1>", "<catalyst 2>"],
  "key_themes": ["<theme 1>", "<theme 2>"],
  "summary": "<2-3 sentence summary of the overall news sentiment and key takeaways>",
  "headline_analysis": [
    {
      "headline": "<headline text>",
      "url": "<full article URL from the search result>",
      "source": "<source name, e.g. Reuters, Bloomberg, CNBC>",
      "published_date": "<date string if available, e.g. 2026-02-15>",
      "impact": "<positive|negative|neutral>",
      "relevance": "<high|medium|low>"
    }
  ],
  "key_developments": ["<development 1>", "<development 2>"],
  "analyst_actions": ["<action 1>", "<action 2>"]
}

Rules:
- sentiment_score: Use the full 1-10 scale. 5 = truly neutral.
- catalysts: Specific upcoming or recent events that could move the stock.
- key_themes: Recurring topics across multiple articles.
- headline_analysis: Analyze the top 5-8 most relevant headlines.
  IMPORTANT: Include the url and source for each headline from the
  search results you found. The url must be the actual article URL.
- key_developments: Major news from the last 24-48 hours.
- analyst_actions: Recent analyst upgrades, downgrades, or price target changes.
- Be objective. Only report facts found in the search results.\
"""


class NewsAgent:
    """News analysis agent using Claude web search.

    Makes a single API call with the web_search tool. Claude finds
    recent articles, reads them, and returns structured analysis.

    Args:
        api_key: Anthropic API key. If None, reads from env.
        cost_tracker: Optional CostTracker for budget management.
        model: Model ID to use. Defaults to Haiku for cost efficiency.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        resolved_key = resolved_key.strip().replace("\n", "").replace("\r", "")
        self.client = anthropic.Anthropic(api_key=resolved_key)
        self.cost_tracker = cost_tracker
        self.model = model

    def analyze(
        self,
        symbol: str,
        lookback_days: int = 7,
        max_articles: int = 20,
    ) -> dict:
        """Analyze recent news for a stock symbol using web search.

        Args:
            symbol: Stock ticker symbol (e.g., "WHR").
            lookback_days: Hint for how far back to search.
            max_articles: Ignored (kept for API compatibility).

        Returns:
            Dict with sentiment, catalysts, themes, headlines, cost.
        """
        logger.info(f"Analyzing news for {symbol} via web search")

        prompt = (
            f"Search for the latest news about {symbol} stock from the "
            f"past {lookback_days} days. Find recent headlines, analyst "
            f"actions, earnings updates, and any catalysts. Then analyze "
            f"the overall sentiment.\n\n"
            f"Provide your analysis as JSON."
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=NEWS_SYSTEM_PROMPT,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error(f"Web search failed for {symbol}: {e}")
            result = self._empty_result(symbol)
            result["summary"] = f"News fetch failed: {e}"
            return result

        # Extract text, sources, and usage from response
        text_parts = []
        sources = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "web_search_tool_result":
                for item in getattr(block, "content", []):
                    if getattr(item, "type", "") == "web_search_result":
                        sources.append({
                            "title": getattr(item, "title", ""),
                            "url": getattr(item, "url", ""),
                        })

        full_text = "\n".join(text_parts)

        # Parse JSON from response
        analysis = self._parse_json(full_text)

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        token_cost = self._token_cost(input_tokens, output_tokens)
        total_cost = token_cost + WEB_SEARCH_COST

        # Record to cost tracker
        if self.cost_tracker:
            self.cost_tracker.record(
                model="haiku",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                component="news_agent",
                description=f"web_search: {symbol} news",
            )

        # Build headlines with URL/source metadata
        headlines = _build_headlines(
            analysis.get("headline_analysis", []), sources
        )

        score = float(analysis.get("sentiment_score", 5.0))
        headline_impacts = [h.get("impact", "neutral") for h in headlines]

        result = {
            "symbol": symbol,
            "headlines": headlines,
            "sentiment_score": score,
            "sentiment_label": analysis.get("sentiment_label", "neutral"),
            "news_sentiment": _build_sentiment_summary(score, headline_impacts),
            "catalysts": analysis.get("catalysts", []),
            "key_themes": analysis.get("key_themes", []),
            "summary": analysis.get("summary", "No analysis available."),
            "headline_analysis": analysis.get("headline_analysis", []),
            "key_developments": analysis.get("key_developments", []),
            "analyst_actions": analysis.get("analyst_actions", []),
            "sources": sources,
            "article_count": len(headlines),
            "provider": "claude_web_search",
            "cost": round(total_cost, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        logger.info(
            f"News analysis complete for {symbol}: "
            f"sentiment={result['sentiment_score']}, "
            f"sources={len(sources)}, "
            f"cost=${total_cost:.4f}"
        )

        return result

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from Claude's response text."""
        text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Handle markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Try extracting JSON object
        if "{" in text and "}" in text:
            start = text.index("{")
            end = text.rindex("}") + 1
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse JSON from web search response")
        return {}

    def _token_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate token cost for Haiku."""
        return (input_tokens / 1_000_000 * 0.25) + (
            output_tokens / 1_000_000 * 1.25
        )

    @staticmethod
    def _empty_result(symbol: str) -> dict:
        """Return empty result when search fails."""
        return {
            "symbol": symbol,
            "headlines": [],
            "sentiment_score": 5.0,
            "sentiment_label": "neutral",
            "news_sentiment": _build_sentiment_summary(5.0, []),
            "catalysts": [],
            "key_themes": [],
            "summary": f"No news found for {symbol}.",
            "headline_analysis": [],
            "key_developments": [],
            "analyst_actions": [],
            "sources": [],
            "article_count": 0,
            "provider": "claude_web_search",
            "cost": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        }


def _build_sentiment_summary(score: float, impacts: list[str]) -> dict:
    """Build a structured sentiment summary with interpretation and breakdown.

    Args:
        score: Sentiment score 1-10.
        impacts: List of headline impact strings ("positive"/"negative"/"neutral").

    Returns:
        Dict with score, interpretation, methodology, breakdown.
    """
    # Interpret score — three-tier labels with colors for frontend
    if score >= 7:
        interpretation = "Bullish"
        color = "green"
    elif score >= 5:
        interpretation = "Neutral"
        color = "gray"
    else:
        interpretation = "Bearish"
        color = "red"

    positive = sum(1 for i in impacts if i == "positive")
    neutral = sum(1 for i in impacts if i == "neutral")
    negative = sum(1 for i in impacts if i == "negative")

    return {
        "score": round(score, 1),
        "max_score": 10,
        "interpretation": interpretation,
        "color": color,
        "methodology": (
            "Analyzes recent news headlines using NLP to gauge market "
            "sentiment. Higher scores indicate more positive coverage."
        ),
        "breakdown": {
            "positive_headlines": positive,
            "neutral_headlines": neutral,
            "negative_headlines": negative,
        },
        "tooltip": (
            "Score ranges: 7-10 Bullish (green), "
            "5-7 Neutral (gray), 0-5 Bearish (red). "
            f"Based on {len(impacts)} recent headlines."
        ),
    }


def _build_headlines(
    headline_analysis: list[dict], sources: list[dict]
) -> list[dict]:
    """Build enriched headline objects with URL and source metadata.

    Uses URLs/sources from Claude's headline_analysis first, then falls
    back to matching against the web_search_tool_result sources list.

    Args:
        headline_analysis: Claude's analyzed headlines (may include url/source).
        sources: Raw web search result sources with title and url.

    Returns:
        List of headline dicts with title, url, source, published_at.
    """
    headlines = []

    for item in headline_analysis:
        title = item.get("headline", "")
        url = item.get("url", "")
        source = item.get("source", "")
        published = item.get("published_date", "")

        # If Claude didn't provide a URL, try to match against sources
        if not url and sources:
            url, matched_source = _match_source(title, sources)
            if not source and matched_source:
                source = matched_source

        headlines.append({
            "title": title,
            "url": url,
            "source": source,
            "published_at": published,
            "impact": item.get("impact", "neutral"),
            "relevance": item.get("relevance", "medium"),
        })

    return headlines


def _match_source(title: str, sources: list[dict]) -> tuple[str, str]:
    """Try to match a headline to a web search source by title similarity.

    Returns:
        (url, source_domain) or ("", "") if no match found.
    """
    if not title or not sources:
        return "", ""

    title_lower = title.lower()
    title_words = set(title_lower.split())

    best_url = ""
    best_source = ""
    best_overlap = 0

    for src in sources:
        src_title = src.get("title", "").lower()
        src_words = set(src_title.split())

        # Count word overlap
        overlap = len(title_words & src_words)
        if overlap > best_overlap and overlap >= 2:
            best_overlap = overlap
            best_url = src.get("url", "")
            # Extract domain as source name
            best_source = _domain_to_source(best_url)

    return best_url, best_source


def _domain_to_source(url: str) -> str:
    """Extract a human-readable source name from a URL."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        # Remove www. prefix
        domain = domain.removeprefix("www.")

        # Map known domains to clean names
        domain_map = {
            "reuters.com": "Reuters",
            "bloomberg.com": "Bloomberg",
            "cnbc.com": "CNBC",
            "wsj.com": "Wall Street Journal",
            "ft.com": "Financial Times",
            "marketwatch.com": "MarketWatch",
            "finance.yahoo.com": "Yahoo Finance",
            "seekingalpha.com": "Seeking Alpha",
            "fool.com": "Motley Fool",
            "barrons.com": "Barron's",
            "investopedia.com": "Investopedia",
            "thestreet.com": "TheStreet",
            "benzinga.com": "Benzinga",
            "tipranks.com": "TipRanks",
            "nasdaq.com": "Nasdaq",
            "nypost.com": "NY Post",
            "cnn.com": "CNN",
            "bbc.com": "BBC",
            "apnews.com": "AP News",
        }

        if domain in domain_map:
            return domain_map[domain]

        # Fall back to cleaned domain
        parts = domain.split(".")
        return parts[0].capitalize() if parts else domain
    except Exception:
        return ""
