"""News analysis agent powered by Claude Haiku.

Fetches recent news for a stock symbol and uses Haiku to summarize headlines,
extract sentiment, identify catalysts, and surface key themes.

Cost target: <$0.10 per analysis (Haiku is cheap).
"""

import json
from typing import Optional

from src.agents.model_wrappers import HaikuWrapper, get_wrapper
from src.utils.cost_tracker import CostTracker
from src.utils.logger import get_logger
from src.utils.news_fetcher import fetch_recent_news

logger = get_logger("news_agent")

NEWS_SYSTEM_PROMPT = """\
You are a financial news analyst. You analyze recent news headlines and articles
about a stock to extract actionable trading insights.

You MUST respond with valid JSON only — no markdown, no explanation, no code fences.

Your response format:
{
  "sentiment_score": <float 1-10, where 1=very bearish, 5=neutral, 10=very bullish>,
  "sentiment_label": "<bearish|slightly_bearish|neutral|slightly_bullish|bullish>",
  "catalysts": ["<catalyst 1>", "<catalyst 2>"],
  "key_themes": ["<theme 1>", "<theme 2>"],
  "summary": "<2-3 sentence summary of the overall news sentiment and key takeaways>",
  "headline_analysis": [
    {"headline": "<headline text>", "impact": "<positive|negative|neutral>", "relevance": "<high|medium|low>"}
  ]
}

Rules:
- sentiment_score: Use the full 1-10 scale. 5 = truly neutral.
- catalysts: Specific upcoming or recent events that could move the stock (earnings, FDA approval, acquisition, etc.)
- key_themes: Recurring topics across multiple articles (margin pressure, growth, restructuring, etc.)
- headline_analysis: Analyze the top 5 most relevant headlines only.
- Be objective. Do not fabricate information not present in the articles.\
"""


class NewsAgent:
    """Haiku-powered news analysis agent.

    Fetches recent news for a symbol and sends headlines to Haiku
    for sentiment analysis, catalyst identification, and theme extraction.

    Args:
        api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        cost_tracker: Optional CostTracker for budget management.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.haiku = get_wrapper("haiku", api_key=api_key, cost_tracker=cost_tracker)
        self.cost_tracker = cost_tracker

    def analyze(
        self,
        symbol: str,
        lookback_days: int = 7,
        max_articles: int = 20,
    ) -> dict:
        """Analyze recent news for a stock symbol.

        Fetches news articles and sends them to Haiku for analysis.

        Args:
            symbol: Stock ticker symbol (e.g., "WHR").
            lookback_days: Number of days to look back for news.
            max_articles: Maximum number of articles to fetch.

        Returns:
            Dict with keys: headlines, sentiment_score, catalysts,
            key_themes, summary, cost.
        """
        logger.info(f"Analyzing news for {symbol} (last {lookback_days} days)")

        # Step 1: Fetch news
        articles = fetch_recent_news(
            symbol=symbol,
            days=lookback_days,
            max_articles=max_articles,
        )

        if not articles:
            logger.warning(f"No news articles found for {symbol}")
            return self._empty_result(symbol)

        # Step 2: Build prompt with articles
        prompt = self._build_prompt(symbol, articles)

        # Step 3: Send to Haiku
        result = self.haiku.call(
            prompt=prompt,
            system=NEWS_SYSTEM_PROMPT,
            max_tokens=2048,
            temperature=0.1,
            component="news_agent",
        )

        # Step 4: Parse response
        analysis = self._parse_response(result["text"], articles)
        analysis["cost"] = result["cost"]
        analysis["input_tokens"] = result["input_tokens"]
        analysis["output_tokens"] = result["output_tokens"]

        logger.info(
            f"News analysis complete for {symbol}: "
            f"sentiment={analysis['sentiment_score']}, "
            f"catalysts={len(analysis['catalysts'])}, "
            f"cost=${result['cost']:.4f}"
        )

        return analysis

    def _build_prompt(self, symbol: str, articles: list[dict]) -> str:
        """Build the analysis prompt from fetched articles.

        Args:
            symbol: Stock ticker symbol.
            articles: List of article dicts from news_fetcher.

        Returns:
            Formatted prompt string.
        """
        lines = [
            f"Analyze the following recent news articles about {symbol} stock.",
            f"There are {len(articles)} articles.\n",
        ]

        for i, article in enumerate(articles, 1):
            lines.append(f"--- Article {i} ---")
            lines.append(f"Title: {article['title']}")
            if article.get("date"):
                lines.append(f"Date: {article['date']}")
            if article.get("source"):
                lines.append(f"Source: {article['source']}")
            if article.get("snippet"):
                lines.append(f"Snippet: {article['snippet'][:300]}")
            lines.append("")

        lines.append(
            f"Provide your analysis of the overall news sentiment for {symbol}."
        )
        return "\n".join(lines)

    def _parse_response(self, text: str, articles: list[dict]) -> dict:
        """Parse Haiku's JSON response into structured output.

        Args:
            text: Raw response text from Haiku.
            articles: Original articles for headline list.

        Returns:
            Parsed analysis dict.
        """
        # Extract JSON from response (handle potential markdown fences)
        json_text = text.strip()
        if json_text.startswith("```"):
            # Remove code fences
            lines = json_text.split("\n")
            json_text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Haiku response as JSON, using defaults")
            parsed = {}

        # Build headlines list from original articles
        headlines = [
            {"title": a["title"], "date": a.get("date", ""), "source": a.get("source", "")}
            for a in articles
        ]

        return {
            "symbol": articles[0].get("title", "").split()[0] if articles else "",
            "headlines": headlines,
            "sentiment_score": float(parsed.get("sentiment_score", 5.0)),
            "sentiment_label": parsed.get("sentiment_label", "neutral"),
            "catalysts": parsed.get("catalysts", []),
            "key_themes": parsed.get("key_themes", []),
            "summary": parsed.get("summary", "No analysis available."),
            "headline_analysis": parsed.get("headline_analysis", []),
            "article_count": len(articles),
        }

    def _empty_result(self, symbol: str) -> dict:
        """Return an empty result when no articles are found.

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Empty analysis dict with default values.
        """
        return {
            "symbol": symbol,
            "headlines": [],
            "sentiment_score": 5.0,
            "sentiment_label": "neutral",
            "catalysts": [],
            "key_themes": [],
            "summary": f"No recent news articles found for {symbol}.",
            "headline_analysis": [],
            "article_count": 0,
            "cost": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
