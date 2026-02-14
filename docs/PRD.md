# Product Requirements Document: Multi-Asset Trading Analysis System

**Version:** 1.0  
**Date:** February 14, 2026  
**Status:** Draft  
**Authors:** Product & Engineering Leadership

---

## 1. Executive Summary

### 1.1 Problem Statement
Traders and investors currently face fragmented workflows when analyzing potential trades:
- Technical analysis requires manual chart review and pattern identification
- Fundamental analysis involves scouring multiple data sources (SEC filings, news, earnings reports)
- No unified view combining technical signals with fundamental catalysts
- Time-consuming process that limits the number of opportunities that can be evaluated

### 1.2 Proposed Solution
A unified, automated analysis system that:
- Ingests TradingView chart data (CSV format)
- Performs comprehensive technical analysis (gaps, S/R levels, supply/demand zones)
- Aggregates and analyzes fundamental data from multiple sources
- Synthesizes both technical and fundamental insights into actionable reports
- Supports multiple asset classes: US Stocks, Options, Crypto, Futures/Commodities

### 1.3 Success Criteria
- **Primary:** Reduce analysis time from hours to minutes per security
- **Quality:** 90%+ accuracy in identifying key technical levels vs. manual analysis
- **Comprehensive:** Surface both bull and bear cases with supporting evidence
- **Actionable:** Generate reports that directly inform trading decisions
- **Extensible:** Modular architecture that allows adding new data sources and analysis techniques

---

## 2. User Personas & Use Cases

### 2.1 Primary Persona: Active Trader/Investor
**Profile:**
- Analyzes 5-20+ securities per week
- Uses technical analysis for entry/exit timing
- Monitors fundamental catalysts for directional bias
- Trades across multiple asset classes
- Values time efficiency and data-driven decisions

**Key Workflows:**
1. **Pre-Market Preparation:** Analyze overnight gaps, news, and upcoming catalysts
2. **Opportunity Screening:** Evaluate potential trades across watchlist
3. **Deep Dive Analysis:** Comprehensive review before position entry
4. **Position Monitoring:** Track active positions for exit signals

### 2.2 Pain Points Being Solved
- **Fragmented Tools:** Currently uses TradingView + SEC.gov + News sites + earnings calendars separately
- **Manual Pattern Recognition:** Spending time identifying gaps and S/R levels manually
- **Information Overload:** Difficulty synthesizing vast amounts of news/fundamental data
- **Recency Bias:** Missing historical context (e.g., gaps from months ago)
- **Incomplete Analysis:** Bull case analysis without adequate bear case consideration

---

## 3. Functional Requirements

### 3.1 Core Features (MVP - Phase 1)

#### 3.1.1 Data Ingestion
- **Input:** TradingView CSV export (OHLCV data)
- **Support:** Multiple timeframes (1min, 5min, 1hour, daily, weekly)
- **Validation:** Data quality checks and anomaly detection

#### 3.1.2 Technical Analysis Engine
- **Gap Detection:** Identify unfilled gaps with severity ranking
- **Support/Resistance:** Calculate key levels using multiple methodologies
  - Pivot points
  - Swing highs/lows
  - Volume profile (if volume data available)
- **Supply/Demand Zones:** Identify institutional accumulation/distribution areas
- **Trend Analysis:** Overall directional bias and strength

#### 3.1.3 Fundamental Analysis Engine
- **News Aggregation:** Recent news relevant to the security
- **Earnings Data:** Latest earnings results and forward guidance
- **Catalyst Identification:** Upcoming events that could move price
- **Sentiment Analysis:** Bull vs. bear case synthesis

#### 3.1.4 Report Generation
- **Markdown Report:** Human-readable analysis
- **JSON Output:** Structured data for programmatic access
- **HTML Dashboard:** Visual presentation with charts

### 3.2 Enhanced Features (Phase 2)

#### 3.2.1 Advanced Technical Analysis
- **Chart Patterns:** Head & shoulders, triangles, flags, wedges
- **Indicator Integration:** RSI, MACD, Bollinger Bands, custom indicators
- **Multi-Timeframe Analysis:** Correlate signals across timeframes
- **Fibonacci Levels:** Retracements and extensions

#### 3.2.2 Deep Fundamental Analysis
- **SEC Filings Parser:** Extract key data from 10-K, 10-Q, 8-K
- **Earnings Call Transcripts:** Analyze management tone and guidance
- **Social Sentiment:** Aggregate sentiment from Twitter/Reddit
- **Economic Calendar:** Macro events affecting the security
- **Sector Analysis:** Relative strength vs. sector peers

#### 3.2.3 Options-Specific Features
- **Implied Volatility Analysis:** IV rank and percentile
- **Options Flow:** Unusual options activity
- **Greeks Analysis:** Delta, gamma, theta, vega exposure

#### 3.2.4 Crypto-Specific Features
- **On-Chain Metrics:** Wallet activity, exchange flows
- **Funding Rates:** Perpetual futures bias
- **Dominance Analysis:** BTC/ETH dominance trends

### 3.3 Future Enhancements (Phase 3+)
- Real-time data integration (replace CSV with live feeds)
- Backtesting capabilities
- Portfolio-level analysis
- Alert system for signal triggers
- Machine learning for pattern recognition improvement
- Multi-security comparative analysis

### 3.4 Out of Scope
- Trading execution (this is analysis only)
- Portfolio management/tracking
- Real-time chat/collaboration features
- Mobile app (desktop/script only for now)

---

## 4. Technical Requirements

### 4.1 Data Inputs & API Sources

**Data Strategy:** Start with free tier, upgrade selectively as needed

| Input Type | MVP (Free) | Production ($) | Recommended for MVP |
|------------|------------|----------------|---------------------|
| **Price Data (OHLCV)** | yfinance (free) | Polygon.io ($99/mo) | yfinance |
| **Options Data** | TD Ameritrade API (free*) | Polygon.io ($99/mo) | TD Ameritrade |
| **Options Flow** | - | Unusual Whales Pro ($39/mo) | Phase 2 upgrade |
| **SEC Filings** | SEC EDGAR (free) | sec-api.io ($99/mo) | SEC EDGAR |
| **Earnings Transcripts** | Web scraping (free) | AlphaSense ($10k+/yr) | Web scraping |
| **News** | Web search (free) | NewsAPI ($449/mo) | Web search |
| **Social Sentiment** | Reddit API (free), StockTwits (free) | Twitter API ($100/mo) | Reddit + StockTwits |
| **Economic Data** | FRED API (free) | Trading Economics ($100/mo) | FRED |
| **Sector/ETF Data** | yfinance (free) | - | yfinance |

*\*Requires TD Ameritrade account (no minimum balance required)*

---

#### 4.1.1 Chart Data APIs

**Option 1: yfinance (Recommended for MVP)**
```python
import yfinance as yf

# Historical data
ticker = yf.Ticker("WHR")
df = ticker.history(period="2y", interval="1mo")  # Monthly
df = ticker.history(period="60d", interval="1d")  # Daily
df = ticker.history(period="7d", interval="5m")   # Intraday

# Pros: Free, easy, works for stocks
# Cons: Not official, rate limited, no futures/crypto
# Cost: FREE
```

**Option 2: Alpha Vantage (Budget Option)**
```python
# Free tier: 25 calls/day
# Premium: $49.99/mo for 75 calls/min
# Supports: Stocks, Forex, Crypto

url = "https://www.alphavantage.co/query"
params = {
    'function': 'TIME_SERIES_DAILY',
    'symbol': 'WHR',
    'apikey': API_KEY
}

# Pros: Free tier available, multiple assets
# Cons: Rate limited on free tier
# Cost: FREE (limited) or $49.99/mo
```

**Option 3: Polygon.io (Production)**
```python
# Real-time + historical
# Stocks, Options, Forex, Crypto
# WebSocket support

from polygon import RESTClient

client = RESTClient(API_KEY)
bars = client.get_aggs("WHR", 1, "day", "2024-01-01", "2024-12-31")

# Pros: Comprehensive, real-time, professional
# Cons: $99/mo minimum
# Cost: $99-199/mo
```

**Decision:** Use yfinance for MVP, upgrade to Polygon if real-time needed

---

#### 4.1.2 Options Data APIs

**Option 1: TD Ameritrade API (Recommended for MVP)**
```python
# FREE with TD account (no minimum balance)
# Includes IV, Greeks, Open Interest

import requests

url = "https://api.tdameritrade.com/v1/marketdata/chains"
params = {
    'symbol': 'WHR',
    'apikey': TD_API_KEY
}

response = requests.get(url, params=params)
chains = response.json()

# Access: Greeks (delta, gamma, theta, vega)
# Access: IV, volume, open interest
# Access: Strike prices, bid/ask

# Pros: FREE, includes Greeks, official data
# Cons: Requires TD account (free to create)
# Cost: FREE
```

**Option 2: yfinance (Basic)**
```python
import yfinance as yf

ticker = yf.Ticker("WHR")
options = ticker.option_chain('2026-03-20')

calls = options.calls  # Strike, Last, Bid, Ask, Volume, OI, IV
puts = options.puts

# Pros: Free, simple
# Cons: No historical IV, delayed, no flow data
# Cost: FREE
```

**Option 3: Polygon.io (Advanced)**
```python
# Historical IV, Greeks, Options flow
# Real-time updates

# Pros: Professional-grade options data
# Cons: $99/mo
# Cost: $99/mo (same subscription as equity data)
```

**Decision:** Use TD Ameritrade API (free) for MVP

---

#### 4.1.3 Options Flow / Unusual Activity

**Option 1: Unusual Whales (Recommended for Phase 2)**
```python
# Unusual options activity
# Dark pool data
# Congress trading
# Market sentiment

# Unusual Whales API
# Pro: $39/mo
# Elite: $99/mo

import requests

url = "https://api.unusualwhales.com/api/..."
headers = {"Authorization": f"Bearer {API_KEY}"}

# Features:
# - Unusual options volume
# - Dark pool blocks
# - Congress stock trades
# - Social sentiment
# - Correlation data

# Pros: Best for options flow, dark pool, congress data
# Cons: $39-99/mo, focused on flow (not historical OHLCV)
# Cost: $39/mo (Pro) or $99/mo (Elite)
```

**Decision:** Skip for MVP, add Unusual Whales Pro ($39) in Phase 2 if options analysis is priority

---

#### 4.1.4 SEC Filings

**Option 1: SEC EDGAR API (Recommended for MVP)**
```python
import requests
from bs4 import BeautifulSoup

# Free, official source
headers = {'User-Agent': 'your_email@example.com'}
url = f"https://data.sec.gov/submissions/CIK{cik}.json"

response = requests.get(url, headers=headers)
filings = response.json()

# Filter for 10-K, 10-Q, 8-K
# Download HTML/XBRL
# Parse with BeautifulSoup + Sonnet LLM

# Pros: FREE, official, comprehensive
# Cons: Requires parsing, rate limited (10 req/sec)
# Cost: FREE
```

**Option 2: sec-api.io (Production)**
```python
from sec_api import QueryApi, ExtractorApi

query_api = QueryApi(api_key=API_KEY)
query = {
    "query": "ticker:WHR AND filedAt:[2024-01-01 TO 2024-12-31]",
    "from": 0,
    "size": 10
}

# Pre-parsed XBRL data
# Clean JSON output

# Pros: Clean data, easy to use
# Cons: $99/mo
# Cost: $99/mo
```

**Decision:** Use SEC EDGAR (free) + Sonnet to parse for MVP

---

#### 4.1.5 Earnings Transcripts

**Option 1: Web Scraping (MVP)**
```python
# Seeking Alpha, Yahoo Finance
# Public transcripts

from bs4 import BeautifulSoup
import requests

url = f"https://seekingalpha.com/symbol/{symbol}/earnings/transcripts"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract transcript text
# Use Sonnet to analyze tone, guidance

# Pros: FREE
# Cons: Legal gray area, may break
# Cost: FREE
```

**Option 2: Company Investor Relations (Official)**
```python
# Direct from company websites
# Requires custom scraping per company

# Pros: FREE, official
# Cons: Inconsistent formats, manual work
# Cost: FREE
```

**Decision:** Web scraping + Sonnet for MVP

---

#### 4.1.6 Social Sentiment

**Option 1: Reddit API (Recommended for MVP)**
```python
import praw

reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_SECRET",
    user_agent="TradingAnalyzer/1.0"
)

# Search subreddits
subreddit = reddit.subreddit('wallstreetbets+stocks+investing')
posts = subreddit.search('WHR', time_filter='week', limit=100)

# Free tier: 60 requests/minute

# Pros: FREE, good coverage, easy API
# Cons: 60 req/min limit
# Cost: FREE
```

**Option 2: StockTwits API (Free)**
```python
import requests

url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
response = requests.get(url)

# Focused on trading/investing
# Pros: FREE, finance-focused
# Cons: Smaller than Reddit
# Cost: FREE
```

**Option 3: Twitter API (Optional)**
```python
# Now requires payment since Elon acquisition
# Basic: $100/mo

# Pros: Broad coverage, real-time
# Cons: $100/mo
# Cost: $100/mo (skip for MVP)
```

**Decision:** Reddit API (free) for MVP, optionally add StockTwits

---

#### 4.1.7 Economic Data

**Option 1: FRED API (Recommended - FREE)**
```python
from fredapi import Fred

fred = Fred(api_key='YOUR_KEY')  # Free API key from St. Louis Fed

# Get economic indicators
gdp = fred.get_series('GDP')
unemployment = fred.get_series('UNRATE')
housing_starts = fred.get_series('HOUST')  # For WHR!
inflation = fred.get_series('CPIAUCSL')

# Macro overlay for analysis

# Pros: FREE, official, comprehensive
# Cons: US-focused
# Cost: FREE
```

**Decision:** FRED API is excellent and free - use for MVP and production

---

### MVP API Cost Summary

| Service | Cost | When to Use |
|---------|------|-------------|
| **yfinance** | FREE | Chart data (stocks) |
| **TD Ameritrade** | FREE* | Options chains + Greeks |
| **SEC EDGAR** | FREE | SEC filings |
| **Reddit API** | FREE | Social sentiment |
| **FRED** | FREE | Economic data |
| **Web Scraping** | FREE | Earnings transcripts, news |
| **TOTAL MVP** | **$0/month** | Full functionality |

*Requires account (no minimum balance)

### Production Upgrade Path

**Phase 2 Upgrade ($39/mo):**
- Add Unusual Whales Pro ($39) for options flow, dark pool, congress

**Phase 3 Upgrade ($138/mo):**
- Keep Unusual Whales Pro ($39)
- Add Polygon.io ($99) for real-time data + crypto

**Enterprise Upgrade ($238+/mo):**
- Keep above ($138)
- Add sec-api.io ($99) for clean SEC data
- Optional: NewsAPI, Twitter API

### 4.2 Data Outputs
| Output Type | Format | Use Case |
|-------------|--------|----------|
| Analysis Report | Markdown | Human review, upload to Claude.ai for discussion |
| Structured Data | JSON | Programmatic consumption, API integration |
| Visual Dashboard | HTML | Interactive exploration with charts |
| Professional Document | PDF | Sharing, archiving, presentations |
| Raw Calculations | CSV | Audit/debugging, custom analysis |

### 4.3 Performance Requirements
- **Analysis Speed:** Complete analysis in <30 seconds for standard dataset
- **Data Freshness:** News/fundamental data <1 hour old (where applicable)
- **Accuracy:** Technical level identification within 0.5% of manual analysis
- **Scalability:** Handle datasets up to 10,000 bars without performance degradation

### 4.4 Dependencies

**Core Requirements:**
```txt
# Python version
python>=3.9

# Data Processing
pandas>=2.0.0
numpy>=1.24.0

# API & Web
requests>=2.31.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0

# LLM
anthropic>=0.18.0

# Config
pyyaml>=6.0
```

**Data Source APIs (MVP - All Free):**
```txt
# Chart Data
yfinance>=0.2.0  # Free stock/ETF data

# Social Sentiment
praw>=7.7.0  # Reddit API (free)

# Economic Data
fredapi>=0.5.0  # FRED API (free)

# SEC Filings
# No package needed - use requests + BeautifulSoup
```

**PDF Export:**
```txt
# Option A: HTML → PDF (Simple)
pdfkit>=1.0.0  # Requires wkhtmltopdf binary

# Option B: Professional PDFs (Advanced)
reportlab>=4.0.0  # Custom PDF generation
```

**Optional Production APIs:**
```txt
# TD Ameritrade (Free but requires account)
# tda-api>=1.2.0

# Polygon.io ($99/mo)
# polygon-api-client>=1.12.0

# Unusual Whales ($39/mo)
# Custom API client (no official package)

# sec-api.io ($99/mo)
# sec-api>=1.0.0
```

**Advanced Technical Analysis (Optional):**
```txt
# Advanced indicators
TA-Lib>=0.4.0  # Requires binary installation

# Charting
plotly>=5.0.0
matplotlib>=3.7.0
```

**Testing & Development:**
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0  # Code formatting
mypy>=1.0.0  # Type checking
```

**Complete requirements.txt for MVP:**
```txt
# Core
pandas>=2.0.0
numpy>=1.24.0
anthropic>=0.18.0
pyyaml>=6.0
python-dotenv>=1.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0

# Data Sources (Free)
yfinance>=0.2.0
praw>=7.7.0
fredapi>=0.5.0

# PDF Export
pdfkit>=1.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### 4.5 Configuration Management
- Config file for API keys, data source preferences
- User preferences for analysis sensitivity/thresholds
- Asset class-specific configuration profiles

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TRADING ANALYZER SYSTEM                  │
└─────────────────────────────────────────────────────────────┘

INPUT LAYER
├── CSV Parser (TradingView data)
├── News Aggregator (API/Scraping)
├── SEC Filing Fetcher
├── Earnings Data Provider
├── Social Sentiment Collector
└── Economic Calendar Fetcher

PROCESSING LAYER
├── Technical Analysis Engine
│   ├── Gap Analyzer
│   ├── Support/Resistance Calculator
│   ├── Supply/Demand Zone Identifier
│   ├── Trend Analyzer
│   └── Pattern Recognition (Phase 2)
│
└── Fundamental Analysis Engine
    ├── News Analyzer
    ├── Earnings Analyzer
    ├── Catalyst Extractor
    ├── Sentiment Synthesizer
    └── SEC Filing Parser (Phase 2)

SYNTHESIS LAYER
├── Bull/Bear Case Generator
├── Risk/Reward Calculator
├── Confluence Detector (technical + fundamental alignment)
└── Priority Ranker

OUTPUT LAYER
├── Markdown Report Generator
├── JSON Exporter
├── HTML Dashboard Builder
└── Visualization Engine

UTILITIES
├── Config Manager
├── Cache Manager
├── Logger
└── Error Handler
```

### 5.2 Data Flow

```
1. USER INITIATES ANALYSIS
   ↓
2. CSV INGESTION → Data Validation → Normalize Format
   ↓
3. PARALLEL PROCESSING:
   ├─→ Technical Analysis (sync)
   └─→ Fundamental Analysis (async API calls)
   ↓
4. SYNTHESIS
   ├─→ Combine technical + fundamental
   ├─→ Generate bull/bear cases
   └─→ Calculate confidence scores
   ↓
5. OUTPUT GENERATION
   ├─→ Markdown report
   ├─→ JSON data
   └─→ HTML dashboard
   ↓
6. DELIVER TO USER
```

### 5.3 Module Interaction Matrix

| Module | Depends On | Provides To |
|--------|-----------|-------------|
| CSV Parser | Config Manager | All analysis modules |
| Gap Analyzer | CSV Parser, Config | Synthesis Layer |
| S/R Calculator | CSV Parser, Config | Synthesis Layer |
| News Aggregator | Config, Cache | Fundamental Engine |
| Earnings Analyzer | Config, News Aggregator | Fundamental Engine |
| Synthesis Engine | All analysis modules | Report Generators |
| Report Generators | Synthesis Engine | User |

---

## 6. Component Specifications

### 6.1 Core Components (MVP)

#### Component 0: Conviction Check (Pre-Analysis)
**Purpose:** Capture user's thesis BEFORE running analysis to enable accountability

**This runs FIRST** - before any analysis occurs. Forces users to articulate their reasoning.

**User Flow:**
```bash
$ python main.py --symbol WHR --csv WHR.csv --tier standard

═══════════════════════════════════════════════════
🎯 CONVICTION CHECK
═══════════════════════════════════════════════════

Before I analyze WHR, I need to understand YOUR thesis.

Why are you considering this trade?

1. What is your PRIMARY reason?
   a) Technical setup (support/resistance, pattern, gap)
   b) Fundamental catalyst (earnings, news, guidance)
   c) Options flow / unusual activity
   d) Macro/sector trend
   e) Just exploring / no specific thesis yet

Your choice: a

2. What SPECIFIC technical setup?
   a) Support bounce
   b) Resistance breakout
   c) Gap fill play
   d) Reversal pattern
   e) Trend continuation
   f) Other: _________

Your choice: a

3. State your thesis in ONE sentence:
> Price will bounce from $88 support level

4. Your conviction level:
   a) High - Ready to trade this
   b) Medium - Leaning but need confirmation
   c) Low - Just researching
   d) None - Curious about analysis

Your choice: b

5. What's your planned stop loss?
> $85 (below support)

═══════════════════════════════════════════════════

✅ Thesis captured. Running analysis...

Your thesis will be evaluated against the data.
```

**Captured Data:**
```python
{
  "symbol": "WHR",
  "user_thesis": {
    "type": "support_bounce",
    "statement": "Price will bounce from $88 support level",
    "conviction": "medium",
    "primary_reason": "technical",
    "stop_loss": 85.00,
    "timestamp": "2026-02-14T10:30:00Z"
  }
}
```

**Optional Mode:**
Users can skip conviction check with `--skip-conviction` flag for exploratory analysis.
When skipped, system provides balanced analysis without thesis validation.

**Implementation:**
```python
class ConvictionChecker:
    """Interactive pre-analysis thesis capture"""
    
    def prompt_user(self) -> Dict:
        """Interactive CLI prompts"""
        
        print("\n" + "="*60)
        print("🎯 CONVICTION CHECK")
        print("="*60)
        
        # Primary reason
        reasons = {
            'a': ('technical', 'Technical setup'),
            'b': ('fundamental', 'Fundamental catalyst'),
            'c': ('options_flow', 'Options flow / unusual activity'),
            'd': ('macro', 'Macro/sector trend'),
            'e': ('exploring', 'Just exploring')
        }
        
        print("\n1. What is your PRIMARY reason?")
        for key, (_, desc) in reasons.items():
            print(f"   {key}) {desc}")
        
        reason_key = input("\nYour choice: ").strip().lower()
        reason_type, _ = reasons.get(reason_key, ('exploring', 'Just exploring'))
        
        # If exploring, skip to analysis
        if reason_type == 'exploring':
            return {
                'type': 'exploratory',
                'statement': 'No specific thesis - exploratory analysis',
                'conviction': 'none',
                'skip_validation': True
            }
        
        # Specific thesis based on reason
        if reason_type == 'technical':
            thesis_type = self._get_technical_thesis_type()
        elif reason_type == 'fundamental':
            thesis_type = self._get_fundamental_thesis_type()
        # ... etc
        
        # Get thesis statement
        statement = input("\n3. State your thesis in ONE sentence:\n> ").strip()
        
        # Get conviction
        conviction_map = {
            'a': 'high',
            'b': 'medium',
            'c': 'low',
            'd': 'none'
        }
        
        print("\n4. Your conviction level:")
        print("   a) High - Ready to trade")
        print("   b) Medium - Leaning but need confirmation")
        print("   c) Low - Just researching")
        print("   d) None - Curious about analysis")
        
        conv_key = input("\nYour choice: ").strip().lower()
        conviction = conviction_map.get(conv_key, 'low')
        
        # Optional: Stop loss
        stop_loss = None
        if thesis_type in ['support_bounce', 'resistance_breakout']:
            stop_input = input("\n5. What's your planned stop loss? (optional)\n> ").strip()
            if stop_input:
                try:
                    stop_loss = float(stop_input.replace('$', ''))
                except:
                    pass
        
        return {
            'type': thesis_type,
            'statement': statement,
            'conviction': conviction,
            'primary_reason': reason_type,
            'stop_loss': stop_loss,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_technical_thesis_type(self) -> str:
        """Drill down into specific technical thesis"""
        
        print("\n2. What SPECIFIC technical setup?")
        print("   a) Support bounce")
        print("   b) Resistance breakout")
        print("   c) Gap fill play")
        print("   d) Reversal pattern")
        print("   e) Trend continuation")
        print("   f) Other")
        
        choice = input("\nYour choice: ").strip().lower()
        
        type_map = {
            'a': 'support_bounce',
            'b': 'resistance_breakout',
            'c': 'gap_fill',
            'd': 'reversal_pattern',
            'e': 'trend_continuation',
            'f': 'other_technical'
        }
        
        return type_map.get(choice, 'support_bounce')
```

---

#### Component 1: CSV Parser
**Purpose:** Ingest and normalize TradingView CSV data

**Inputs:**
- File path to CSV
- Asset class identifier (stock/crypto/futures/options)

**Outputs:**
- Pandas DataFrame with standardized columns: `[datetime, open, high, low, close, volume]`
- Metadata: symbol, timeframe, data quality score

**Key Functions:**
- `load_csv(file_path)` → DataFrame
- `validate_data(df)` → quality_score, errors[]
- `normalize_columns(df)` → standardized DataFrame
- `extract_metadata(df, filename)` → {symbol, timeframe, date_range}

**Dependencies:** pandas, datetime

**Error Handling:**
- Missing required columns
- Data gaps/anomalies
- Incorrect timeframe detection

---

#### Component 2: Gap Analyzer
**Purpose:** Identify and rank unfilled price gaps

**Inputs:**
- Normalized DataFrame
- Gap significance threshold (default: 2%)

**Outputs:**
- List of gaps: `[{date, gap_size, gap_type, filled_date, priority}]`
- Gap severity score (1-10)

**Key Functions:**
- `detect_gaps(df)` → gaps[]
- `classify_gap_type(gap)` → "breakaway" | "continuation" | "exhaustion" | "common"
- `check_gap_filled(gap, current_price)` → boolean, fill_percentage
- `prioritize_gaps(gaps)` → sorted by significance

**Logic:**
```python
# Gap detection
for i in range(1, len(df)):
    if df['low'][i] > df['high'][i-1]:  # Gap up
        gap = {
            'type': 'gap_up',
            'size': df['low'][i] - df['high'][i-1],
            'date': df['time'][i],
            'upper': df['low'][i],
            'lower': df['high'][i-1]
        }
    elif df['high'][i] < df['low'][i-1]:  # Gap down
        # Similar logic
```

**No LLM Cost:** Pure Python/math

---

#### Component 3: Support/Resistance Calculator
**Purpose:** Calculate key price levels using multiple methodologies

**Inputs:**
- DataFrame with OHLC data
- Lookback period (default: 100 bars)
- Sensitivity (default: medium)

**Outputs:**
- S/R levels: `[{price, type, strength, touches, last_test_date}]`
- Zone ranges (supply/demand areas)

**Methodologies:**
1. **Pivot Points:** High/low swing points
2. **Volume Profile:** Price levels with high volume
3. **Round Numbers:** Psychological levels ($50, $100, etc.)
4. **Moving Average Clusters:** Where multiple MAs converge

**Key Functions:**
- `find_swing_points(df, window=5)` → pivots[]
- `calculate_volume_nodes(df)` → high_volume_areas[]
- `detect_round_numbers(current_price)` → levels[]
- `calculate_level_strength(level, df)` → score 1-10

**No LLM Cost:** Pure Python/math

---

#### Component 4: Supply/Demand Zone Identifier
**Purpose:** Identify institutional accumulation/distribution areas

**Inputs:**
- DataFrame with OHLC + Volume
- Zone sensitivity

**Outputs:**
- Supply zones: `[{price_range, volume_profile, strength}]`
- Demand zones: similar structure

**Logic:**
- Sharp price moves from a narrow range = institutional order
- High volume → followed by low volume = absorption
- Rally-base-rally or Drop-base-drop patterns

**Key Functions:**
- `detect_price_explosions(df)` → explosive_moves[]
- `find_base_zones(df)` → consolidation_areas[]
- `calculate_zone_strength(zone)` → score

**No LLM Cost:** Pure Python/math

---

#### Component 5: News Aggregator (Haiku 4.5)
**Purpose:** Collect and summarize recent news

**Inputs:**
- Symbol
- Timeframe (determines lookback: intraday=24hr, daily=7d, weekly=30d, monthly=90d)
- News sources config

**Outputs:**
- News summary: `{headline, date, source, sentiment, relevance_score, summary}`[]
- Aggregated sentiment: bull/neutral/bear

**Data Sources:**
- Web search for recent news
- Financial news APIs (Alpha Vantage, Finnhub, NewsAPI)
- Company press releases
- Sector-specific news

**LLM Usage (Haiku):**
```python
# For each batch of 10-20 articles
prompt = f"""
Summarize these {len(articles)} news articles about {symbol}.
For each article provide:
1. One-sentence summary
2. Sentiment: bullish/neutral/bearish
3. Relevance: high/medium/low
4. Key catalysts mentioned

Articles:
{articles}
"""
# Cost: ~$0.05-0.15 per symbol
```

**Dependencies:** requests, anthropic SDK

---

#### Component 6: SEC Filing Analyzer (Sonnet 4.5)
**Purpose:** Parse and extract key insights from SEC filings

**Inputs:**
- Symbol
- Filing types: 10-K, 10-Q, 8-K
- Lookback period

**Outputs:**
- Financial metrics: revenue, earnings, guidance
- Risk factors (new vs. previous)
- Management discussion & analysis (MD&A) summary
- Forward-looking statements

**Data Sources:**
- SEC EDGAR API
- Pre-downloaded filings

**LLM Usage (Sonnet):**
```python
# For 10-Q/10-K (complex documents)
prompt = f"""
Analyze this {filing_type} for {symbol}.

Extract:
1. Key financial metrics (revenue, earnings, cash flow)
2. YoY and QoQ changes
3. Management guidance for next quarter/year
4. New risk factors not in previous filing
5. Capital allocation plans (buybacks, dividends, capex)
6. Forward-looking statements

Focus on material changes and future outlook.

Filing text:
{filing_text[:50000]}  # Truncate if needed
"""
# Cost: ~$0.40-0.80 per filing
```

**Optimization:**
- Use prompt caching for large filings
- Cache parsed data for 90 days

---

#### Component 7: Earnings Analyzer (Sonnet 4.5)
**Purpose:** Analyze earnings calls and extract forward guidance

**Inputs:**
- Symbol
- Earnings call transcript or earnings release

**Outputs:**
- Beat/miss metrics
- Guidance (raised/lowered/maintained)
- Management tone (confident/cautious/defensive)
- Key growth initiatives
- Analyst questions/concerns

**LLM Usage (Sonnet):**
```python
prompt = f"""
Analyze this earnings call for {symbol}.

Extract:
1. EPS and Revenue: Beat or miss expectations?
2. Guidance for next quarter and full year
3. Management tone: confident, cautious, or defensive?
4. Key growth drivers mentioned
5. Challenges or headwinds discussed
6. Notable analyst questions and management responses

Transcript:
{transcript_text}
"""
# Cost: ~$0.15-0.40 per call
```

---

#### Component 8: Social Sentiment Analyzer (Haiku 4.5)
**Purpose:** Gauge retail investor sentiment from social media

**Inputs:**
- Symbol
- Platforms: Reddit (r/stocks, r/wallstreetbets), Twitter/X
- Timeframe

**Outputs:**
- Sentiment score: -100 to +100
- Volume of mentions (trending or not)
- Key themes/narratives
- Contrarian signals (extreme sentiment)

**Data Sources:**
- Reddit API
- Twitter API (if available)
- StockTwits
- Web scraping (with rate limits)

**LLM Usage (Haiku):**
```python
# Process 50-100 social posts
prompt = f"""
Analyze sentiment for {symbol} from these social media posts.

For each post, classify:
- Sentiment: bullish/neutral/bearish
- Conviction: high/medium/low
- Reason: technical/fundamental/meme/other

Then summarize:
1. Overall sentiment score (-100 to +100)
2. Main bull thesis from community
3. Main bear thesis from community
4. Is sentiment extreme? (contrarian signal)

Posts:
{posts}
"""
# Cost: ~$0.05-0.15 per symbol
```

---

#### Component 9: Catalyst Extractor (Haiku 4.5)
**Purpose:** Identify upcoming events that could move price AND define specific triggers

**This is enhanced with "What Needs to Happen" framework** - not just listing catalysts, but defining specific outcomes needed for bull/bear cases.

**Inputs:**
- Symbol
- Economic calendar (FRED API)
- Company events calendar
- Sector events
- User's thesis (to tailor analysis)

**Outputs:**
- Upcoming catalysts: `[{date, event_type, expected_impact}]`
- **Bull scenario triggers** (what specifically needs to happen)
- **Bear scenario triggers** (what specifically needs to happen)
- **Algorithmic triggers** (keywords/metrics that move algos)
- **Leading indicators** (what to watch BEFORE the catalyst)

**Event Types:**
- Earnings dates
- Product launches
- FDA approvals (pharma)
- Economic data (Fed meetings, jobs report, housing starts)
- Sector conferences
- Mergers/acquisitions
- Regulatory decisions

**Enhanced Catalyst Format:**
```python
{
  "event": "Q1 Earnings",
  "date": "2026-04-20",
  "type": "earnings",
  
  # NEW: "What Needs to Happen" Framework
  "bull_scenario": {
    "needs_to_happen": [
      "EPS beat by $0.10+ (consensus $2.15, need $2.25+)",
      "Gross margin >19% (currently 18.5%)",
      "Guidance raise for full year",
      "Management mentions 'housing recovery' or 'strong demand'"
    ],
    "probability_if_happens": "High - historical beat rate 65%",
    "price_reaction_if_happens": "Target $105-110 achievable",
    "leading_indicators": [
      {
        "indicator": "Housing Starts (FRED:HOUST)",
        "threshold": ">1.5M annualized",
        "current": "1.38M",
        "impact": "Leads WHR demand by 3-6 months"
      }
    ]
  },
  
  "bear_scenario": {
    "needs_to_happen": [
      "EPS miss or in-line with no raise",
      "Margin compression continues (<18%)",
      "Lower guidance due to tariffs/housing",
      "Inventory buildup mentioned"
    ],
    "probability_if_happens": "High",
    "price_reaction_if_happens": "Retest $71 support",
    "warning_signs": [
      "Existing home sales declining",
      "Appliance PPI rising (margin pressure)"
    ]
  },
  
  # NEW: Algorithmic Triggers
  "algorithmic_triggers": [
    "EPS surprise >5% → Momentum algos buy within seconds",
    "Revenue miss → Quant models exit",
    "Guidance keywords: 'strong demand' = bullish trigger",
    "Guidance keywords: 'challenging environment' = bearish trigger"
  ],
  
  # NEW: Why User Should Care
  "relevance_to_user_thesis": "Critical - your bounce thesis needs Q1 beat to justify. Without it, support at $88 may fail."
}
```

**LLM Usage (Haiku):**
```python
prompt = f"""
From this economic calendar and company events, identify catalysts for {symbol}.

USER'S THESIS: {user_thesis['statement']}

For EACH catalyst, provide:

1. BASIC INFO:
   - Date
   - Event type
   - Expected impact: high/medium/low

2. BULL SCENARIO - "What Needs to Happen":
   Specific outcomes needed for bull case:
   - Exact thresholds (e.g., "EPS >$2.25", "Margin >19%")
   - Management commentary keywords
   - Historical context (beat rate, typical reaction)
   - Price target if this occurs
   
3. BEAR SCENARIO - "What Needs to Happen":
   Specific outcomes that trigger bear case:
   - Miss thresholds
   - Warning signs
   - Typical reaction if this occurs
   
4. ALGORITHMIC TRIGGERS:
   What keywords or metrics trigger algo trading?
   - "Strong demand" vs "challenging environment"
   - Beat/miss thresholds that move momentum algos
   - Guidance raise vs lower
   
5. LEADING INDICATORS:
   What should we watch BEFORE this catalyst?
   - Economic data that leads company performance
   - Sector peer results
   - Input cost trends
   
6. RELEVANCE TO USER:
   How does this catalyst affect their stated thesis?

Calendar:
{calendar_data}

Economic indicators available (FRED):
{fred_indicators}

Be SPECIFIC with numbers and thresholds.
Don't say "earnings beat" - say "EPS >$2.25 vs consensus $2.15"
"""
# Cost: ~$0.05-0.10 per symbol (more complex than basic extraction)
```

**Example Output:**
```json
{
  "catalysts": [
    {
      "date": "2026-04-20",
      "event": "Q1 2026 Earnings",
      "type": "earnings",
      "impact": "high",
      
      "bull_needs_to_happen": [
        "EPS >$2.25 (consensus $2.15, +4.7% beat)",
        "Revenue >$4.8B (consensus $4.7B)",
        "Gross margin >19% (Q4 was 18.5%)",
        "Guidance: FY26 EPS $9.50+ (current $9.20)",
        "Management: 'Housing recovery underway' or similar"
      ],
      
      "bear_needs_to_happen": [
        "EPS <$2.10 (consensus $2.15, miss)",
        "Revenue miss + margin compression",
        "Guidance lowered to $9.00 or below",
        "Management: 'Challenging demand environment'"
      ],
      
      "algo_triggers": [
        "EPS surprise >5% → Buy programs activate",
        "Whisper $2.20 → beat whisper = stronger reaction",
        "Keywords: 'strong' 'recovery' 'improving' = +2-3%",
        "Keywords: 'challenging' 'headwinds' 'weak' = -3-5%"
      ],
      
      "leading_indicators": [
        {
          "name": "Housing Starts",
          "symbol": "FRED:HOUST",
          "watch_for": "Trend above 1.5M = positive for WHR",
          "current": "1.38M (below threshold)"
        },
        {
          "name": "Existing Home Sales",
          "symbol": "FRED:EXHOSLUSM495S",
          "watch_for": ">5.5M = replacement cycle strong",
          "current": "5.2M"
        }
      ],
      
      "relevance_to_user": "CRITICAL for your $88 support bounce thesis. If Q1 misses, support may fail. If Q1 beats strongly, validates bounce thesis."
    },
    
    {
      "date": "2026-03-18",
      "event": "Fed Interest Rate Decision",
      "type": "macro",
      "impact": "medium",
      
      "bull_needs_to_happen": [
        "25bps rate cut (currently 4.75%)",
        "Powell: 'Economy achieving soft landing'",
        "Dot plot shows 2-3 cuts in 2026"
      ],
      
      "bear_needs_to_happen": [
        "No cut + hawkish language",
        "Dot plot shows <2 cuts",
        "Inflation concerns persist"
      ],
      
      "algo_triggers": [
        "Rate cut → Consumer discretionary algos buy",
        "'Patient' = neutral, 'data-dependent' = neutral",
        "'Restrictive' = bearish for cyclicals"
      ],
      
      "relevance_to_user": "Medium. Rate cuts help WHR (housing/consumer spending) but not primary driver vs earnings."
    }
  ]
}
```

**Integration:** Output feeds into Opus synthesis to build bull/bear scenarios with specific triggers.

---

#### Component 10: Synthesis Engine (Opus 4.6)
**Purpose:** Combine all signals into evidence-based bull/bear thesis + validate user's stated thesis

**Inputs:**
- **User's stated thesis** (from conviction check)
- Technical signals (gaps, S/R, indicators)
- Fundamental analysis (filings, earnings)
- News sentiment
- Social sentiment
- Catalysts

**Outputs:**
- **Evidence Scorecard** (supporting/contradicting/missing evidence)
- **Quality Checklist** (thesis-specific criteria with transparent assessment)
- Bull case (detailed narrative with supporting factors)
- Bear case (detailed narrative with supporting factors)
- **Evidence-based assessment** (NO fake percentages)
- Risk/reward ratio
- Actionable recommendations
- Critical questions for user

**Critical Design Principle:**
**NO FAKE PERCENTAGES.** Instead of saying "45% probability," use:
- Evidence ratios (3 supporting vs 7 contradicting)
- Checklists (1 out of 9 criteria met)
- Strength ratings (STRONG, MODERATE, WEAK, VERY WEAK)
- Transparent factor counts

**LLM Usage (Opus):**
```python
prompt = f"""
You are analyzing {symbol} on the {timeframe} timeframe.

USER'S STATED THESIS:
Type: {user_thesis['type']}  # e.g., "support_bounce"
Statement: "{user_thesis['statement']}"  # e.g., "Price will bounce from $88"
Conviction: {user_thesis['conviction']}  # high/medium/low

TECHNICAL ANALYSIS:
{technical_summary}

FUNDAMENTAL ANALYSIS:
{fundamental_summary}

NEWS SENTIMENT:
{news_summary}

SOCIAL SENTIMENT:
{social_summary}

UPCOMING CATALYSTS:
{catalysts}

Your task is to:

1. EVIDENCE SCORECARD (for user's thesis):
   
   SUPPORTING EVIDENCE:
   - List every factor that supports their thesis
   - Be specific (e.g., "RSI oversold at 39.83" not "RSI favorable")
   
   CONTRADICTING EVIDENCE:
   - List every factor that contradicts their thesis
   - Include the magnitude (e.g., "7% below 200 SMA" not "below 200 SMA")
   
   MISSING CRITICAL ELEMENTS:
   - What's undefined? (stop loss, confirmation signal, catalyst, etc.)
   - What data is absent? (volume confirmation, pattern, etc.)
   
   EVIDENCE RATIO:
   - Count: X supporting vs Y contradicting
   - DO NOT convert to percentages
   - State clearly: "More evidence supports" or "More evidence contradicts"

2. QUALITY CHECKLIST (thesis-specific):

   For a {user_thesis['type']} play, standard criteria include:
   
   TECHNICAL CRITERIA:
   [ ] Historical significance of level
   [ ] Volume confirmation
   [ ] Oscillator alignment (oversold/overbought)
   [ ] Reversal pattern present
   [ ] Moving average structure
   
   FUNDAMENTAL CRITERIA:
   [ ] Catalyst present
   [ ] Fundamentals improving/deteriorating
   
   RISK MANAGEMENT:
   [ ] Stop loss defined
   [ ] Risk/reward >2:1
   
   For EACH criterion:
   - Mark as MET, NOT MET, or MIXED
   - Explain why with specific data
   - Note the risk if not met
   
   SCORE: X out of Y criteria met
   ASSESSMENT: 
   - >70% = STRONG setup
   - 50-70% = MODERATE setup
   - 30-50% = WEAK setup
   - <30% = VERY WEAK setup

3. BULL CASE:
   
   THESIS: [One sentence thesis]
   
   SUPPORTING FACTORS: (list specific evidence)
   - [Technical factor with data]
   - [Fundamental factor with data]
   - [Catalyst with date/impact]
   
   WHAT NEEDS TO HAPPEN: (specific triggers)
   - [Specific price/event with threshold]
   - [Leading indicator to watch]
   - [Confirmation signal needed]
   
   TARGET: $X with specific timeframe
   STRENGTH: [STRONG/MODERATE/WEAK based on factor count]
   RISKS: [What invalidates this case]

4. BEAR CASE:
   
   [Same structure as bull case]

5. SYNTHESIS & RECOMMENDATION:
   
   EVIDENCE COMPARISON:
   - Bull case has X supporting factors
   - Bear case has Y supporting factors
   - User's thesis has Z:W evidence ratio
   
   HONEST ASSESSMENT:
   - Which case has stronger support from the data?
   - How does user's thesis compare to the evidence?
   - What's the quality score (from checklist)?
   
   RECOMMENDATION:
   - Action: [WAIT/ENTER/PASS] with clear rationale
   - If WAIT: what needs to improve?
   - If ENTER: what's the risk management plan?
   - Better alternative entry if applicable

6. CRITICAL QUESTIONS:
   
   Based on gaps in user's thesis, ask:
   - [Specific question about undefined elements]
   - [Challenge on weak criteria]
   - [Request clarification on edge]

IMPORTANT RULES:
- NO percentages unless you can show the math
- NO "45% probability" - use "MODERATE strength with 4 factors"
- DO show evidence counts (3 vs 7, not 30%)
- DO be transparent about methodology
- DO challenge weak setups constructively
- DO provide specific, actionable recommendations

Be honest. If the setup is weak, say so clearly.
If user's conviction doesn't match data, point it out.
"""
# Cost: ~$1.00-2.00 per symbol
```

**Example Output Structure:**
```python
{
  "thesis_evaluation": {
    "user_thesis": "Price will bounce from $88 support",
    "scorecard": {
      "supporting": [
        {"factor": "RSI oversold (39.83)", "detail": "Bounce potential"},
        {"factor": "Held $88 for 2 days", "detail": "Weak support forming"}
      ],
      "contradicting": [
        {"factor": "$88 never tested before", "detail": "No historical significance"},
        {"factor": "No volume spike", "detail": "Declining volume (-40%)"},
        {"factor": "Below 200 SMA by 7%", "detail": "Bearish structure"}
        # ... more
      ],
      "missing": [
        {"element": "Stop loss undefined"},
        {"element": "No confirmation signal defined"}
      ],
      "ratio": "2 supporting vs 7 contradicting",
      "assessment": "WEAK - Evidence contradicts thesis 3.5:1"
    },
    
    "quality_checklist": {
      "criteria_met": 1,
      "criteria_total": 9,
      "details": [
        {
          "criterion": "Historical Support",
          "met": false,
          "analysis": "$88 never tested as support. Nearest proven: $80",
          "risk": "No guarantee institutions defend this level"
        }
        # ... all 9 criteria
      ],
      "assessment": "VERY WEAK - Only 11% criteria met"
    }
  },
  
  "bull_case": {
    "thesis": "Bounce from demand zone + earnings beat",
    "supporting_factors": [
      "Demand zone $71-76 held",
      "Q4 EPS beat by $0.12",
      "RSI oversold bounce potential"
    ],
    "what_needs_to_happen": [
      "Reclaim $82.84 (200 SMA) on volume",
      "Q1 earnings beat with guidance raise",
      "Housing starts >1.5M annualized"
    ],
    "target": 112.00,
    "timeframe": "3-6 months",
    "strength_assessment": "MODERATE - 4 supporting factors but needs confirmation"
  },
  
  "bear_case": {
    "thesis": "Below MAs + housing weakness + margin pressure",
    "supporting_factors": [
      "Below all major MAs",
      "Guidance lowered Q4",
      "Margin compression (18.5% vs 19.3%)",
      "Housing concerns persist",
      "No volume confirmation"
    ],
    "strength_assessment": "STRONG - 7 supporting factors align"
  },
  
  "recommendation": {
    "action": "WAIT",
    "rationale": [
      "User's thesis only 1/9 criteria met",
      "Evidence ratio 2:7 against",
      "Bear case stronger (7 vs 4 factors)"
    ],
    "better_entry": {
      "level": "$80-82",
      "criteria": ["Proven support", "Volume spike", "Reversal pattern"],
      "improvement": "Would meet 5/9 criteria vs current 1/9"
    }
  },
  
  "critical_questions": [
    "Why $88 when data shows $80 is proven support?",
    "What's your edge with only 1/9 criteria?",
    "Where's your stop loss?"
  ]
}
```

---

#### Component 11: Report Generator (Sonnet 4.5)
**Purpose:** Create formatted outputs (Markdown, JSON, HTML, PDF)

**Inputs:**
- Synthesis output (including thesis evaluation)
- All component outputs
- User preferences (format, verbosity)

**Outputs:**
- **Markdown:** Human-readable report with Evidence Scorecard + Checklist
- **JSON:** Structured data for programmatic use
- **HTML:** Interactive dashboard
- **PDF:** Professional document export

**Report Structure (Markdown):**

```markdown
# {SYMBOL} Analysis Report
## Generated: {DATE} | Tier: {TIER} | Timeframe: {TIMEFRAME}

═══════════════════════════════════════════════════
📋 YOUR THESIS
═══════════════════════════════════════════════════
**Type:** {thesis_type}
**Your Statement:** "{user_thesis_statement}"
**Your Conviction:** {conviction_level}
**Stop Loss:** {stop_loss if defined}

═══════════════════════════════════════════════════
⚖️ EVIDENCE SCORECARD
═══════════════════════════════════════════════════

**SUPPORTING EVIDENCE:**
✅ {factor_1} - {detail}
✅ {factor_2} - {detail}
✅ {factor_3} - {detail}

**CONTRADICTING EVIDENCE:**
❌ {factor_1} - {detail}
❌ {factor_2} - {detail}
❌ {factor_3} - {detail}
[... more ...]

**MISSING CRITICAL ELEMENTS:**
⚠️ {missing_element_1}
⚠️ {missing_element_2}
⚠️ {missing_element_3}

**EVIDENCE SUMMARY:**
- Supporting factors: {count}
- Contradicting factors: {count}
- Missing key elements: {count}

**RATIO: {X} Supporting vs {Y} Contradicting ({ratio} against/for)**

**INITIAL ASSESSMENT:** {assessment_icon} {ASSESSMENT}
{explanation}

═══════════════════════════════════════════════════
📋 QUALITY CHECKLIST: {THESIS_TYPE}
═══════════════════════════════════════════════════

For a {thesis_type} play, professional traders look for:

**TECHNICAL CRITERIA:**

[ ] 1. {Criterion Name}
    {✅ MET / ❌ NOT MET / ⚠️ MIXED}
    
    Requirement: {what's needed}
    
    Analysis: {specific analysis with data}
    
    {⚠️ Risk: {risk if not met}}

---

[✓] 2. {Criterion Name}
    ✅ MET
    
    Requirement: {what's needed}
    
    Analysis: {why it's met with data}
    
    ✅ {positive note}

[... 7-9 more criteria ...]

═══════════════════════════════════════════════════
📊 CHECKLIST SCORE
═══════════════════════════════════════════════════

**CRITERIA MET: {X} out of {Y}** ({percentage}%)

✅ Met: {count}
❌ Not Met: {count}
⚠️ Mixed/Uncertain: {count}

**BREAKDOWN BY CATEGORY:**

Technical ({count} criteria):
• Met: {count}
• Not Met: {count}
• Score: {X}/{Y} ({percentage}%)

Fundamental ({count} criteria):
• Met: {count}
• Not Met: {count}
• Score: {X}/{Y} ({percentage}%)

Risk Management ({count} criteria):
• Met: {count}
• Not Met: {count}
• Score: {X}/{Y} ({percentage}%)

**ASSESSMENT LOGIC:**
- Score >70% = STRONG setup
- Score 50-70% = MODERATE setup
- Score 30-50% = WEAK setup
- Score <30% = VERY WEAK setup

**VERDICT: {ASSESSMENT} - {interpretation}**

═══════════════════════════════════════════════════
⚠️ HONEST ASSESSMENT
═══════════════════════════════════════════════════

**SETUP QUALITY: {ASSESSMENT}**

{Detailed explanation of what this means}

**THIS DOESN'T MEAN IT'S IMPOSSIBLE**
{Context about why weak setups can still work}

**BUT it means:**
{Specific risks and implications}

═══════════════════════════════════════════════════
📈 TECHNICAL ANALYSIS
═══════════════════════════════════════════════════

**Current Price:** ${price}
**Trend:** {trend_assessment}

**Key Levels:**
- Resistance: ${levels}
- Support: ${levels}

**Gaps:**
{gap_analysis}

**Supply/Demand Zones:**
{zone_analysis}

═══════════════════════════════════════════════════
📊 FUNDAMENTAL ANALYSIS
═══════════════════════════════════════════════════

**Latest Earnings:** {earnings_summary}
**Recent News:** {news_summary}
**Social Sentiment:** {sentiment_summary}

═══════════════════════════════════════════════════
🐂 BULL CASE
═══════════════════════════════════════════════════

**THESIS:** {bull_thesis}

**SUPPORTING FACTORS:**
{bullet_list_of_factors_with_data}

**WHAT NEEDS TO HAPPEN:**
{specific_triggers_and_thresholds}

**TARGET:** ${target} | Timeframe: {timeframe}
**STRENGTH:** {STRONG/MODERATE/WEAK} - {factor_count} supporting factors

═══════════════════════════════════════════════════
🐻 BEAR CASE
═══════════════════════════════════════════════════

**THESIS:** {bear_thesis}

**SUPPORTING FACTORS:**
{bullet_list_of_factors_with_data}

**TARGET:** ${target} | Timeframe: {timeframe}
**STRENGTH:** {STRONG/MODERATE/WEAK} - {factor_count} supporting factors

═══════════════════════════════════════════════════
🎯 RECOMMENDATIONS
═══════════════════════════════════════════════════

**OPTION 1: {RECOMMENDATION_TITLE}**

Rationale: {explanation}

Actions:
• {action_1}
• {action_2}
• {action_3}

---

**OPTION 2: {RECOMMENDATION_TITLE}**

{same structure}

---

**OPTION 3: {RECOMMENDATION_TITLE}**

{same structure}

═══════════════════════════════════════════════════
❓ QUESTIONS FOR YOU
═══════════════════════════════════════════════════

Before you decide:

1. **{Question based on weak criteria}**
   {Follow-up context}

2. **{Question about edge}**
   {Follow-up context}

3. **{Question about undefined elements}**
   {Follow-up context}

4. **{Question about conviction mismatch}**
   {Follow-up context}

═══════════════════════════════════════════════════
💬 INTERACTIVE DISCUSSION MODE
═══════════════════════════════════════════════════

I've challenged your thesis. Now let's discuss.

**Upload this report to Claude.ai and let's debate:**

Ready-to-ask questions:
• "Defend my thesis - what am I seeing that you're not?"
• "What if I'm willing to accept the weak setup?"
• "Show me historical examples where this worked"
• "Help me build a better entry strategy"
• "What would make this setup acceptable?"

<analysis_data>
```json
{full_analysis_data_for_chat_context}
```
</analysis_data>

═══════════════════════════════════════════════════
📌 UPCOMING CATALYSTS
═══════════════════════════════════════════════════

{catalyst_list_with_dates_and_impact}

═══════════════════════════════════════════════════
⚠️ DISCLAIMER
═══════════════════════════════════════════════════

This analysis is for informational purposes only and does not 
constitute financial advice. Trading involves substantial risk.
Past performance does not guarantee future results.

═══════════════════════════════════════════════════
```

**LLM Usage (Sonnet):**
```python
# Generate markdown report structure
prompt = f"""
Create a professional trading analysis report for {symbol}.

USER'S THESIS (from conviction check):
{user_thesis}

THESIS EVALUATION (from validator):
{thesis_validation_results}

ANALYSIS RESULTS:
{all_analysis_results}

Generate a markdown report following this EXACT structure:

1. Thesis Summary (user's stated thesis)
2. Evidence Scorecard (supporting/contradicting/missing)
3. Quality Checklist (detailed criterion-by-criterion)
4. Checklist Score (transparent metrics)
5. Honest Assessment (what the score means)
6. Technical Analysis
7. Fundamental Analysis
8. Bull Case
9. Bear Case
10. Recommendations (3 options)
11. Questions for User (challenge their thinking)
12. Interactive Discussion Mode (with embedded JSON)
13. Upcoming Catalysts
14. Disclaimer

Use the template formatting with ═══ dividers and emojis as shown.

Be HONEST about weak setups. Challenge the user constructively.
No fake percentages - use evidence ratios and checklist scores.
"""
# Cost: ~$0.10-0.25 per report
```

**JSON Output Structure:**
```json
{
  "symbol": "WHR",
  "generated_at": "2026-02-14T10:45:00Z",
  "tier": "standard",
  "timeframe": "monthly",
  
  "user_thesis": {
    "type": "support_bounce",
    "statement": "Price will bounce from $88 support",
    "conviction": "medium",
    "stop_loss": 85.00
  },
  
  "thesis_evaluation": {
    "scorecard": {
      "supporting": [...],
      "contradicting": [...],
      "missing": [...],
      "ratio": "3 vs 7",
      "assessment": "WEAK"
    },
    "checklist": {
      "score_met": 1,
      "score_total": 9,
      "score_percentage": 11.1,
      "assessment": "VERY_WEAK",
      "criteria_results": [...]
    }
  },
  
  "technical": {...},
  "fundamental": {...},
  "bull_case": {...},
  "bear_case": {...},
  "recommendations": [...],
  "questions": [...],
  "catalysts": [...]
}
```

**PDF Export (New Feature):**
```python
# Option A: HTML → PDF (reuses HTML generation)
import pdfkit

def generate_pdf(analysis_report, filename):
    """Convert HTML report to PDF"""
    
    # Generate HTML first
    html = generate_html_report(analysis_report)
    
    # Convert to PDF
    pdfkit.from_string(html, filename)
    
    return filename

# Option B: ReportLab (professional formatting)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf_professional(analysis, filename):
    """Generate PDF with custom formatting"""
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    story.append(Paragraph(
        f"{analysis.symbol} Analysis Report", 
        styles['Title']
    ))
    
    # Evidence Scorecard section
    story.append(Paragraph("Evidence Scorecard", styles['Heading1']))
    story.append(Paragraph(
        f"Supporting: {len(analysis.scorecard.supporting)}<br/>"
        f"Contradicting: {len(analysis.scorecard.contradicting)}",
        styles['Normal']
    ))
    
    # ... build rest of report
    
    doc.build(story)
    return filename
```

**Cost:** ~$0.10-0.30 per report generation

---

#### Component 12: Thesis Validation Framework (NEW - Critical for Accountability)
**Purpose:** Validate user's stated thesis using transparent, evidence-based checklists

**This is a KEY differentiator** - forces users to articulate and defend their thesis BEFORE getting analysis.

**Inputs:**
- User's stated thesis (from conviction check)
- Analysis results (technical + fundamental)
- Thesis type (support_bounce, breakout, gap_fill, earnings_catalyst, options_flow, etc.)

**Outputs:**
1. **Evidence Scorecard** (quick visual summary)
2. **Quality Checklist** (detailed thesis-specific criteria)
3. **Recommendations** (3 actionable options)
4. **Critical Questions** (challenges to user's thinking)

**Key Principle: NO FAKE PERCENTAGES**

❌ BAD: "Your thesis has 30% of supporting evidence"
✅ GOOD: "Your thesis meets 1 out of 9 standard criteria. You have 3 supporting factors vs 7 contradicting factors. This is a WEAK setup."

**Why No Percentages:**
- Where did 30% come from? What's 100%?
- Creates false precision
- Implies mathematical rigor that doesn't exist
- Misleads users into thinking it's quantitative

**Instead We Use:**
- Evidence ratios (3 supporting vs 7 contradicting)
- Checklists (1 out of 9 criteria met = 11%)
- Strength ratings (STRONG, MODERATE, WEAK, VERY WEAK)
- Transparent factor counts

---

### 12.1 Evidence Scorecard (Quick Summary)

**Purpose:** Immediate visual assessment at top of report

**Format:**
```markdown
═══════════════════════════════════════════════════
⚖️ EVIDENCE SCORECARD
═══════════════════════════════════════════════════

**SUPPORTING EVIDENCE:**
✅ RSI oversold (39.83) - bounce potential
✅ Price held $88 for 2 days - weak support forming
✅ Demand zone nearby ($71-76) - safety net

**CONTRADICTING EVIDENCE:**
❌ $88 never tested as support before - no historical significance
❌ No volume confirmation - declining volume, not spiking
❌ Below 200 SMA ($82.84) - bearish trend structure
❌ All major MAs trending down - momentum against you
❌ No bullish reversal pattern - just sideways drift
❌ No fundamental catalyst - no reason for bounce here
❌ Guidance lowered last quarter - fundamental weakness

**MISSING CRITICAL ELEMENTS:**
⚠️ Stop loss not defined - where do you exit if wrong?
⚠️ Volume spike absent - no institutional buying
⚠️ No confirmation signal - what proves the bounce?

**EVIDENCE SUMMARY:**
- Supporting factors: 3
- Contradicting factors: 7
- Missing key elements: 3

**RATIO: 3 Supporting vs 7 Contradicting (2.3:1 against)**

**INITIAL ASSESSMENT:** ⚠️ WEAK SETUP
More evidence contradicts your thesis than supports it.
```

---

### 12.2 Quality Checklist (Detailed Analysis)

**Purpose:** Transparent, criterion-by-criterion evaluation

**Methodology:**
1. Select thesis-type checklist (support bounce, breakout, etc.)
2. Evaluate each criterion with specific data
3. Mark as MET ✅, NOT MET ❌, or MIXED ⚠️
4. Explain WHY with specifics
5. Note the RISK if not met
6. Calculate transparent score

**Example: Support Bounce Checklist**

```markdown
═══════════════════════════════════════════════════
📋 SUPPORT BOUNCE QUALITY CHECKLIST
═══════════════════════════════════════════════════

For a high-probability support bounce play, professional 
traders typically look for these criteria:

**TECHNICAL CRITERIA:**

[ ] 1. Historical Support Level
    ❌ NOT MET
    
    Requirement: Price level tested as support 2+ times before
    
    Analysis: $88.00 has NEVER been tested as support in WHR's
    history. This is a new, unproven level.
    
    The nearest proven support levels are:
    • $80.00 (tested 1x in Nov 2025)
    • $71.63 (tested 2x, strong base)
    
    ⚠️ Risk: Without historical precedent, you don't know if 
    institutions will defend this level.

---

[✓] 3. Oversold Indicator
    ✅ MET
    
    Requirement: RSI <40 or similar oversold reading
    
    Analysis: RSI = 39.83 (oversold territory)
    • Last oversold bounce: RSI 37 → rallied 18%
    • Typical bounce zone: RSI 30-40
    
    ✅ This IS a positive signal for bounce potential

[... 7 more criteria ...]

═══════════════════════════════════════════════════
📊 CHECKLIST SCORE
═══════════════════════════════════════════════════

**CRITERIA MET: 1 out of 9** (11%)

✅ Met: 1
❌ Not Met: 7
⚠️ Mixed/Uncertain: 1

**BREAKDOWN BY CATEGORY:**

Technical (5 criteria):
• Met: 1 (Oversold indicator)
• Not Met: 4 (Historical support, Volume, Pattern, MA structure)
• Score: 1/5 (20%)

Fundamental (2 criteria):
• Met: 0
• Not Met: 1 (No catalyst)
• Mixed: 1 (Fundamentals mixed)
• Score: 0/2 (0%)

Risk Management (2 criteria):
• Met: 0
• Not Met: 2 (No stop, can't calculate R:R)
• Score: 0/2 (0%)

**ASSESSMENT LOGIC:**
- Score >70% (7/9+) = STRONG setup
- Score 50-70% (5-6/9) = MODERATE setup
- Score 30-50% (3-4/9) = WEAK setup
- Score <30% (0-2/9) = VERY WEAK setup

**VERDICT: VERY WEAK - Only 11% criteria met**
```

---

### 12.3 Thesis-Specific Checklists (Complete Definitions)

Each thesis type has a standardized checklist. Below are the complete specifications:

#### Checklist A: Support Bounce Play

**Total Criteria: 9**

**Technical (5 criteria):**
1. **Historical Support** - Level tested 2+ times as support
2. **Volume Spike** - Volume increasing as price approaches support
3. **Oversold Indicator** - RSI <40, Stochastic <20, or similar
4. **Bullish Reversal Pattern** - Hammer, morning star, engulfing, etc.
5. **MA Structure** - Above major MAs or clearly reclaiming them

**Fundamental (2 criteria):**
6. **Positive Catalyst** - Recent news, earnings, or event supporting bounce
7. **Improving Fundamentals** - Revenue/margins/guidance trending positive

**Risk Management (2 criteria):**
8. **Stop Loss Defined** - Clear invalidation point identified
9. **Risk/Reward >2:1** - Potential reward >2x the risk

---

#### Checklist B: Resistance Breakout Play

**Total Criteria: 9**

**Technical (5 criteria):**
1. **Strong Resistance** - Level tested 2+ times, rejected
2. **Volume Surge** - Volume >150% of average on breakout
3. **Consolidation Pattern** - Clear base-building before breakout
4. **Momentum Alignment** - RSI >50, MACD positive, ADX rising
5. **Follow-Through** - Second day confirms with higher close

**Fundamental (2 criteria):**
6. **Catalyst Present** - News/earnings driving breakout
7. **Institutional Buying** - Large volume, options flow bullish

**Risk Management (2 criteria):**
8. **Stop at Resistance** - Stop just below broken resistance
9. **Target Defined** - Measured move or next resistance identified

---

#### Checklist C: Gap Fill Play

**Total Criteria: 8**

**Technical (5 criteria):**
1. **Gap Type** - Breakaway (strongest) vs exhaustion vs runaway
2. **Gap Size** - >3% for significance
3. **Days Since Gap** - Recent gaps (<30 days) fill faster
4. **Trend Toward Gap** - Price moving toward gap (not away)
5. **S/R at Gap** - Support/resistance at gap level

**Fundamental (1 criterion):**
6. **Gap Reason** - Understand why gap occurred (earnings? news?)

**Risk Management (2 criteria):**
7. **Stop Beyond Gap** - Stop loss past the gap on failure
8. **Partial Fill Strategy** - Plan for partial vs full fill

---

#### Checklist D: Earnings Catalyst Play

**Total Criteria: 10**

**Fundamental (5 criteria):**
1. **Beat History** - Company beats estimates >60% of time
2. **Consensus vs Whisper** - Whisper number expectations
3. **Guidance Track Record** - Management typically raises/lowers?
4. **Revenue Quality** - Not just EPS beat, revenue matters
5. **Sector Performance** - Sector peers also beating?

**Technical (2 criteria):**
6. **Pre-Earnings Setup** - Strong base vs weakening trend
7. **IV Rank** - Implied volatility percentile (for options traders)

**Options Flow (1 criterion):**
8. **Unusual Activity** - Large call/put buying before earnings

**Risk Management (2 criteria):**
9. **Position Sizing** - Account for earnings volatility
10. **Post-Earnings Plan** - Hold through or sell before?

---

#### Checklist E: Options Flow / Unusual Activity Play

**Total Criteria: 9**

**Options Signals (5 criteria):**
1. **Flow Size** - Unusual volume (>5x average)
2. **Buyer/Seller Initiated** - Aggressive buying (at ask) vs selling
3. **Contract Type** - Calls (bullish) vs Puts (bearish)
4. **Expiration Date** - Near-term (<30 days) = urgent vs long-term
5. **Strike Selection** - ATM (conviction) vs OTM (lotto)

**Confirmation (2 criteria):**
6. **Dark Pool Activity** - Large block trades aligning
7. **Technical Setup** - Flow aligns with technical levels

**Risk Management (2 criteria):**
8. **Flow Reliability** - Not just one whale, sustained interest
9. **Stop if Flow Reverses** - Exit if flow disappears

---

### 12.4 Implementation Specifications

**File: `src/validators/thesis_validator.py`**

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ThesisType(Enum):
    SUPPORT_BOUNCE = "support_bounce"
    RESISTANCE_BREAKOUT = "resistance_breakout"
    GAP_FILL = "gap_fill"
    EARNINGS_CATALYST = "earnings_catalyst"
    OPTIONS_FLOW = "options_flow"
    MACRO_TREND = "macro_trend"

class AssessmentLevel(Enum):
    VERY_WEAK = "VERY WEAK"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"

@dataclass
class Criterion:
    """Single checklist criterion"""
    name: str
    description: str
    requirement: str
    weight: str  # 'high', 'medium', 'low'
    category: str  # 'technical', 'fundamental', 'risk_management', 'options'

@dataclass
class CriterionResult:
    """Result of evaluating a criterion"""
    criterion: Criterion
    met: bool  # True = ✅, False = ❌
    analysis: str  # Detailed explanation with data
    risk_note: Optional[str] = None  # What's the risk if not met?

@dataclass
class EvidenceScorecard:
    """Quick visual summary"""
    supporting: List[Dict[str, str]]  # [{"factor": "...", "detail": "..."}]
    contradicting: List[Dict[str, str]]
    missing: List[str]
    ratio_text: str  # "3 supporting vs 7 contradicting"
    assessment: str  # "WEAK SETUP - Evidence contradicts 2.3:1"

@dataclass
class ChecklistResult:
    """Complete checklist evaluation"""
    criteria_results: List[CriterionResult]
    score_met: int
    score_total: int
    score_percentage: float  # For internal use, not shown to user as standalone
    breakdown: Dict[str, Dict]  # By category
    assessment: AssessmentLevel
    interpretation: str

class ThesisValidator:
    """Validates user thesis using Evidence Scorecard + Checklist Method"""
    
    # Checklist definitions
    SUPPORT_BOUNCE_CHECKLIST = [
        Criterion(
            name="Historical Support",
            description="Level tested 2+ times before",
            requirement="Price level has proven support history",
            weight="high",
            category="technical"
        ),
        # ... 8 more criteria
    ]
    
    # Similar for BREAKOUT_CHECKLIST, GAP_FILL_CHECKLIST, etc.
    
    def validate(
        self, 
        user_thesis: Dict,
        analysis_results: Dict
    ) -> Dict:
        """
        Main validation entry point
        
        Returns:
        {
            'scorecard': EvidenceScorecard,
            'checklist': ChecklistResult,
            'recommendations': List[Dict],
            'questions': List[str]
        }
        """
        # 1. Generate Evidence Scorecard
        scorecard = self._generate_scorecard(
            user_thesis,
            analysis_results
        )
        
        # 2. Run Quality Checklist
        checklist = self._run_checklist(
            user_thesis['type'],
            analysis_results
        )
        
        # 3. Generate Recommendations
        recommendations = self._generate_recommendations(
            scorecard,
            checklist,
            user_thesis
        )
        
        # 4. Generate Critical Questions
        questions = self._generate_questions(
            user_thesis,
            scorecard,
            checklist
        )
        
        return {
            'scorecard': scorecard,
            'checklist': checklist,
            'recommendations': recommendations,
            'questions': questions
        }
    
    def _generate_scorecard(
        self, 
        thesis: Dict, 
        results: Dict
    ) -> EvidenceScorecard:
        """Generate Evidence Scorecard"""
        
        supporting = []
        contradicting = []
        missing = []
        
        # Analyze each data point
        # Technical
        if results['technical']['rsi'] < 40:
            supporting.append({
                'factor': f"RSI oversold ({results['technical']['rsi']:.2f})",
                'detail': "Bounce potential"
            })
        
        if not results['technical']['has_historical_support']:
            contradicting.append({
                'factor': f"${thesis['level']} never tested as support before",
                'detail': "No historical significance"
            })
        
        # ... more logic for all data points
        
        # Calculate ratio
        s_count = len(supporting)
        c_count = len(contradicting)
        ratio = f"{s_count} supporting vs {c_count} contradicting"
        
        if c_count > s_count:
            ratio_value = c_count / s_count if s_count > 0 else float('inf')
            assessment = f"WEAK SETUP - Evidence contradicts {ratio_value:.1f}:1"
        else:
            assessment = "Setup has supporting evidence"
        
        return EvidenceScorecard(
            supporting=supporting,
            contradicting=contradicting,
            missing=missing,
            ratio_text=ratio,
            assessment=assessment
        )
    
    def _run_checklist(
        self,
        thesis_type: ThesisType,
        results: Dict
    ) -> ChecklistResult:
        """Run thesis-specific checklist"""
        
        # Select appropriate checklist
        if thesis_type == ThesisType.SUPPORT_BOUNCE:
            checklist = self.SUPPORT_BOUNCE_CHECKLIST
        elif thesis_type == ThesisType.RESISTANCE_BREAKOUT:
            checklist = self.BREAKOUT_CHECKLIST
        # ... etc
        
        criteria_results = []
        
        for criterion in checklist:
            result = self._check_criterion(criterion, results)
            criteria_results.append(result)
        
        # Calculate score
        met_count = sum(1 for r in criteria_results if r.met)
        total = len(criteria_results)
        percentage = (met_count / total) * 100
        
        # Determine assessment
        if percentage >= 70:
            assessment = AssessmentLevel.STRONG
        elif percentage >= 50:
            assessment = AssessmentLevel.MODERATE
        elif percentage >= 30:
            assessment = AssessmentLevel.WEAK
        else:
            assessment = AssessmentLevel.VERY_WEAK
        
        return ChecklistResult(
            criteria_results=criteria_results,
            score_met=met_count,
            score_total=total,
            score_percentage=percentage,
            breakdown=self._calculate_breakdown(criteria_results),
            assessment=assessment,
            interpretation=f"{assessment.value} - {met_count}/{total} criteria met"
        )
    
    def _check_criterion(
        self,
        criterion: Criterion,
        results: Dict
    ) -> CriterionResult:
        """Check single criterion against data"""
        
        if criterion.name == "Historical Support":
            level = results['user_thesis']['level']
            support_levels = results['technical']['support_levels']
            
            # Check if level has been tested before
            historical = any(
                abs(s['price'] - level) < (level * 0.02) and s['tests'] >= 2
                for s in support_levels
            )
            
            if historical:
                analysis = f"${level} has been tested {X} times as support"
                return CriterionResult(
                    criterion=criterion,
                    met=True,
                    analysis=analysis,
                    risk_note=None
                )
            else:
                nearest = self._find_nearest_support(level, support_levels)
                analysis = (
                    f"${level} has NEVER been tested as support. "
                    f"Nearest proven support: ${nearest['price']} "
                    f"(tested {nearest['tests']}x)"
                )
                risk = (
                    "Without historical precedent, no guarantee "
                    "institutions defend this level"
                )
                return CriterionResult(
                    criterion=criterion,
                    met=False,
                    analysis=analysis,
                    risk_note=risk
                )
        
        # ... similar logic for all criteria
    
    def _generate_recommendations(
        self,
        scorecard: EvidenceScorecard,
        checklist: ChecklistResult,
        thesis: Dict
    ) -> List[Dict]:
        """Generate 3 actionable recommendations"""
        
        recommendations = []
        
        if checklist.score_met < checklist.score_total * 0.3:
            # Very weak setup - offer alternatives
            
            # Option 1: Wait for better setup
            recommendations.append({
                'title': 'WAIT FOR BETTER SETUP (Recommended)',
                'rationale': f'Only {checklist.score_met}/{checklist.score_total} criteria met',
                'actions': self._build_better_setup(checklist, thesis)
            })
            
            # Option 2: Proceed with extreme caution
            recommendations.append({
                'title': 'PROCEED WITH EXTREME CAUTION',
                'rationale': 'If you must enter despite weak setup',
                'actions': [
                    'Use 25% of normal position size',
                    'Define strict stop loss',
                    'Accept this is LOW conviction, not medium',
                    'Be ready to exit immediately if wrong'
                ]
            })
            
            # Option 3: Redefine thesis
            recommendations.append({
                'title': 'REDEFINE YOUR THESIS',
                'rationale': 'Right direction, wrong execution',
                'actions': self._suggest_alternative_thesis(thesis, checklist)
            })
        
        return recommendations
    
    def _generate_questions(
        self,
        thesis: Dict,
        scorecard: EvidenceScorecard,
        checklist: ChecklistResult
    ) -> List[str]:
        """Generate critical questions to challenge user"""
        
        questions = []
        
        # Based on unmet criteria
        for result in checklist.criteria_results:
            if not result.met and result.criterion.weight == 'high':
                questions.append(
                    f"Why proceed without {result.criterion.name}? "
                    f"{result.risk_note}"
                )
        
        # Based on evidence ratio
        if len(scorecard.contradicting) > len(scorecard.supporting):
            questions.append(
                f"You have {len(scorecard.contradicting)} contradicting factors "
                f"vs {len(scorecard.supporting)} supporting. What's your edge?"
            )
        
        # Based on missing elements
        for missing in scorecard.missing:
            questions.append(f"You haven't defined {missing}. What's your plan?")
        
        return questions[:5]  # Max 5 questions
```

**Integration:** This validator is called after technical/fundamental analysis completes, before Opus synthesis.

---

## 6.4 Thesis Validation Framework (CORE DIFFERENTIATOR)

**Purpose:** Force user accountability and evidence-based decision making through transparent thesis evaluation

This framework is what transforms the system from "just another analysis tool" into a **trading accountability partner**.

### The Problem with Typical Analysis

Most analysis tools provide information but don't challenge the user's assumptions or force articulation of their thesis. This leads to:
- Poorly defined entry rationale
- Cognitive biases going unchecked
- Emotional decisions disguised as analysis
- No accountability for bad setups

### Our Solution: Two-Part Validation System

**Part 1: Evidence Scorecard** (Quick Visual)
- Supporting factors: X
- Contradicting factors: Y  
- Missing elements: Z
- Clear ratio (e.g., "3 vs 7 against")

**Part 2: Detailed Checklist** (Criterion-by-Criterion)
- 9 specific criteria across 3 categories
- Each criterion: met/not met/mixed with detailed analysis
- Score: X out of 9 (NOT a percentage)
- Interpretation: STRONG/MODERATE/WEAK/VERY WEAK

### Why NO Percentages?

**We explicitly avoid fake precision:**

❌ BAD: "Your thesis has 30% of supporting evidence"
- Based on what? Where did 30% come from?
- What constitutes 100%?
- False precision undermines credibility

✅ GOOD: "Your thesis meets 1 out of 9 standard criteria. You have 3 supporting factors vs 7 contradicting factors. This is a VERY WEAK setup."
- Transparent methodology
- User can verify every claim
- Actionable and honest

### Thesis Types & Checklists

We maintain specific checklists for each thesis type:

1. **Support Bounce** (9 criteria)
   - Historical support level tested 2+ times?
   - Volume spike on approach?
   - Oversold indicator confirmation?
   - Bullish reversal pattern?
   - Moving average structure favorable?
   - Positive fundamental catalyst?
   - Improving fundamentals?
   - Stop loss defined?
   - Risk/reward >2:1?

2. **Resistance Breakout** (9 criteria)
   - Historical resistance tested multiple times?
   - Volume breakout (>2x average)?
   - Clean break vs false breakout?
   - Retest of breakout level?
   - Moving averages aligned?
   - Catalyst for breakout?
   - Sector strength confirmation?
   - Target defined?
   - Risk/reward >2:1?

3. **Gap Fill Play** (9 criteria)
   - Gap type identified (breakaway/runaway/exhaustion)?
   - Gap age and fill probability?
   - Support/resistance at gap?
   - Volume pattern on gap?
   - Fundamental reason for fill?
   - Timeframe reasonable?
   - Multiple gaps present?
   - Stop placement clear?
   - Risk/reward adequate?

4. **Earnings Catalyst** (9 criteria)
   - Historical earnings reaction pattern?
   - Consensus estimates vs whisper?
   - Recent guidance trends?
   - Sector comps performance?
   - IV rank and crush risk?
   - Expected move calculated?
   - Entry timing (pre/post earnings)?
   - Position sizing for volatility?
   - Multiple scenarios planned?

5. **Options Flow Play** (9 criteria)
   - Unusual activity confirmed?
   - Smart money vs retail indicator?
   - Time to expiration reasonable?
   - Strike selection logic?
   - Flow aligned with technical?
   - Adequate liquidity?
   - IV vs HV comparison?
   - Greeks understood?
   - Exit plan defined?

### User Flow

**Step 1: Conviction Check (Mandatory)**

```
═══════════════════════════════════════════════════
🎯 CONVICTION CHECK
═══════════════════════════════════════════════════

Why are you considering this trade?

1. Primary reason:
   a) Technical setup
   b) Fundamental catalyst
   c) Options flow
   d) Macro/sector trend
   e) Just exploring

2. Specific thesis type:
   a) Support bounce
   b) Resistance breakout
   c) Gap fill
   d) Earnings play
   e) Other

3. State your thesis in one sentence:
   > _________________________________________

4. Your conviction:
   a) High - Ready to trade
   b) Medium - Leaning but need confirmation
   c) Low - Just researching
```

**Step 2: Evidence Scorecard Generation**

System generates quick visual assessment:

```markdown
═══════════════════════════════════════════════════
⚖️ EVIDENCE SCORECARD
═══════════════════════════════════════════════════

**SUPPORTING EVIDENCE:**
✅ RSI oversold (39.83) - bounce potential
✅ Price held $88 for 2 days - weak support forming
✅ Demand zone nearby ($71-76) - safety net

**CONTRADICTING EVIDENCE:**
❌ $88 never tested as support before
❌ No volume confirmation
❌ Below 200 SMA - bearish structure
❌ All MAs trending down
❌ No bullish reversal pattern
❌ No fundamental catalyst
❌ Guidance lowered last quarter

**MISSING CRITICAL ELEMENTS:**
⚠️ Stop loss not defined
⚠️ Volume spike absent
⚠️ No confirmation signal

**EVIDENCE SUMMARY:**
- Supporting: 3
- Contradicting: 7
- Missing: 3

**RATIO: 3 vs 7 (2.3:1 against)**

**INITIAL ASSESSMENT: VERY WEAK SETUP**
More evidence contradicts your thesis than supports it.
```

**Step 3: Detailed Checklist Evaluation**

Each criterion gets detailed analysis:

```markdown
═══════════════════════════════════════════════════
📋 SUPPORT BOUNCE QUALITY CHECKLIST
═══════════════════════════════════════════════════

[ ] 1. Historical Support Level
    ❌ NOT MET
    
    Requirement: Level tested as support 2+ times before
    
    Analysis: $88.00 has NEVER been tested as support in 
    WHR's history. This is a new, unproven level.
    
    Nearest proven support:
    • $80.00 (tested 1x in Nov 2025)
    • $71.63 (tested 2x, Aug + Nov 2025)
    
    ⚠️ Risk: Without historical precedent, institutions 
    may not defend this level.

---

[✓] 3. Oversold Indicator
    ✅ MET
    
    Requirement: RSI <40 or similar oversold
    
    Analysis: RSI = 39.83 (oversold territory)
    • Last oversold bounce: RSI 37 → +18% over 3 weeks
    • Typical bounce zone: RSI 30-40
    
    ✅ Historical precedent supports bounce potential

---

[Continue for all 9 criteria...]

═══════════════════════════════════════════════════
📊 CHECKLIST SCORE
═══════════════════════════════════════════════════

**CRITERIA MET: 1 out of 9**

Breakdown by category:
• Technical (5 criteria): 1/5 met (20%)
• Fundamental (2 criteria): 0/2 met (0%)  
• Risk Management (2 criteria): 0/2 met (0%)

**SETUP QUALITY: VERY WEAK**

When only 1 out of 9 criteria are met, this is NOT a 
high-probability setup by professional standards.
```

**Step 4: Recommendations**

```markdown
═══════════════════════════════════════════════════
🎯 RECOMMENDATIONS
═══════════════════════════════════════════════════

**OPTION 1: WAIT FOR BETTER SETUP (Recommended)**

What would make this 6/9 (acceptable)?

1. Price drops to $80 (proven support) ✅
2. Volume spikes >25M on test ✅
3. Bullish hammer forms ✅
4. RSI positive divergence ✅
5. Reclaim $82.84 (200 SMA) ✅
6. Set stop at $78 ✅

NOW: 7/9 criteria = STRONG setup

---

**OPTION 2: PROCEED WITH CAUTION**

If you MUST enter despite 1/9:

1. Use 25% of normal position size
2. Define stop: $80 (10% risk)
3. Set alert for $82.84 reclaim
4. Accept LOW conviction
5. Exit fast if wrong

R:R = 0.85:1 (POOR)

---

**OPTION 3: REDEFINE THESIS**

Better thesis: "Wait for $80 with volume + 200 SMA reclaim, 
THEN enter for $105+ target"

Same direction, better execution = 7/9 criteria
```

**Step 5: Challenging Questions**

```markdown
═══════════════════════════════════════════════════
❓ QUESTIONS FOR YOU
═══════════════════════════════════════════════════

1. **Why $88 specifically?**
   Data shows $80 and $71.63 are real support. 
   Why not wait for proven levels?

2. **What's your edge?**
   With 1/9 criteria met, what do you know that 
   the market doesn't?

3. **What confirms the bounce?**
   Without volume/pattern/catalyst, what PROVES 
   this is the bottom?

4. **Can you afford to be wrong?**
   No stop + poor R:R = what's your plan if 
   this drops 10-20%?

5. **Why Medium conviction?**
   You said "Medium" but data shows "Very Weak". 
   Where's the disconnect?
```

### Technical Implementation

**Component: ThesisValidator Class**

```python
class ThesisValidator:
    """Validates user thesis using Evidence Scorecard + Checklist"""
    
    CHECKLISTS = {
        'support_bounce': SupportBounceChecklist(),
        'resistance_breakout': BreakoutChecklist(),
        'gap_fill': GapFillChecklist(),
        'earnings_catalyst': EarningsCatalystChecklist(),
        'options_flow': OptionsFlowChecklist()
    }
    
    def validate(self, user_thesis: Dict, analysis: Dict) -> Dict:
        """
        Main validation function
        
        Returns:
            {
                'scorecard': Evidence scorecard,
                'checklist': Detailed criteria results,
                'recommendations': 3 options,
                'questions': 5 challenging questions
            }
        """
        # Select appropriate checklist
        checklist = self.CHECKLISTS[user_thesis['type']]
        
        # Generate Evidence Scorecard
        scorecard = self._build_scorecard(user_thesis, analysis)
        
        # Run detailed checklist
        results = checklist.evaluate(analysis)
        
        # Generate recommendations based on score
        recs = self._build_recommendations(results, user_thesis)
        
        # Generate challenging questions
        questions = self._build_questions(user_thesis, results)
        
        return {
            'scorecard': scorecard,
            'checklist': results,
            'score': f"{results.met}/{results.total}",
            'assessment': self._interpret_score(results),
            'recommendations': recs,
            'questions': questions
        }
    
    def _interpret_score(self, results) -> str:
        """Interpret checklist score honestly"""
        ratio = results.met / results.total
        
        if ratio >= 0.7:
            return "STRONG - Most criteria met"
        elif ratio >= 0.5:
            return "MODERATE - Mixed signals"
        elif ratio >= 0.3:
            return "WEAK - More against than for"
        else:
            return "VERY WEAK - Not recommended"
```

**Component: Criterion Class**

```python
@dataclass
class Criterion:
    """Single checklist criterion"""
    name: str
    requirement: str
    weight: str  # 'high', 'medium', 'low'
    category: str  # 'technical', 'fundamental', 'risk_management'
    
@dataclass  
class CriterionResult:
    """Result of checking a criterion"""
    criterion: Criterion
    met: bool
    analysis: str
    risk_note: Optional[str] = None
```

### Catalyst Enhancement: "What Needs to Happen"

**Extension to catalyst analysis:**

Traditional approach:
```
Upcoming Catalyst: Q1 Earnings (Apr 20, 2026)
Type: Earnings release
Impact: High
```

**Enhanced approach:**

```markdown
═══════════════════════════════════════════════════
📅 UPCOMING CATALYST: Q1 Earnings
═══════════════════════════════════════════════════

**Date:** April 20, 2026 (After Market Close)
**Type:** Quarterly earnings release
**Estimated Impact:** HIGH

**BULL SCENARIO - What needs to happen:**

Quantitative triggers:
• EPS >$2.25 (consensus $2.15, need beat by $0.10+)
• Revenue >$4.9B (consensus $4.8B)
• Gross margin >19% (currently 18.5%)
• Guidance RAISE for full year

Qualitative triggers:
• Management mentions "housing recovery signs"
• "Strong demand" language = algo buy trigger
• Positive commentary on margins
• No mention of tariff concerns

**If ALL happen:**
• Probability: 65% → 85% bull case
• Price target: $115 → $130
• Expected move: +15-20%

**BEAR SCENARIO - What needs to happen:**

Quantitative triggers:
• EPS miss or in-line (≤$2.15)
• Revenue miss (<$4.7B)
• Margin compression (<18%)
• Guidance LOWER for full year

Qualitative triggers:
• "Cautious outlook" language
• Inventory buildup mentioned
• Tariff/input cost concerns
• Housing headwinds emphasized

**If MOST happen:**
• Probability: 35% → 60% bear case
• Price target: $71 → $60
• Expected move: -15-25%

**ALGORITHMIC TRIGGERS:**

Pattern recognition:
• Beat >5% → Momentum algos buy within 5min
• Miss any amount → Quant models exit
• Guidance keywords: "strong" = buy, "cautious" = sell
• Margin expansion = institutional buy signal

**LEADING INDICATORS (Watch BEFORE earnings):**

1. **Housing Starts** (FRED:HOUST)
   • Current: 1.43M annualized
   • Bull threshold: >1.5M
   • Lead time: 3-6 months before WHR demand
   
2. **Existing Home Sales**
   • Current: 5.2M annualized  
   • Bull threshold: >5.5M
   • Drives replacement cycle
   
3. **Consumer Confidence**
   • Current: 102.5
   • Bull threshold: >105
   • Indicates discretionary spending

**YOUR ACTION PLAN:**

Pre-earnings (now → Apr 19):
• Monitor housing starts monthly releases
• Track home sales (released mid-month)
• Watch sector comps (Lowe's, Home Depot)

Day of earnings:
• Review actual vs all bull/bear triggers above
• Calculate probabilities in real-time
• Adjust thesis accordingly

Post-earnings:
• If bull scenario: Consider entry on confirmation
• If bear scenario: Reassess or wait for $71-76
• If mixed: Wait for clarity
```

### Why This Matters

**Traditional Analysis:**
> "WHR might bounce from support. Consider buying."

**Our Framework:**
> "You want to buy WHR at $88. Let's evaluate that thesis:
> 
> Your thesis meets only 1 out of 9 standard criteria for a support bounce. You have 3 factors supporting vs 7 contradicting. This is a VERY WEAK setup.
>
> Specifically: $88 has never been tested as support before, volume is declining (not spiking), there's no reversal pattern, you're below all major MAs, and there's no fundamental catalyst.
>
> Your conviction says 'Medium' but the evidence says 'Very Weak'. Before risking capital, answer: Why $88? What's your edge? What confirms the bounce?
>
> Recommended: Wait for $80 (proven level) with volume spike and 200 SMA reclaim. That would be a 7/9 setup vs your current 1/9."

**The difference:**
- Forces articulation of thesis
- Provides evidence-based pushback
- Shows exactly what's missing
- Offers path to better setup
- Creates accountability

### Success Metrics for This Feature

- **User Behavior:** % of users who modify their thesis after seeing checklist
- **Setup Quality:** Average checklist score of executed trades (target >5/9)
- **Learning:** Improvement in thesis quality over time per user
- **Accountability:** % of users who wait for better setups when shown weak scores
- **Engagement:** Discussion mode usage after thesis challenge

**This is what makes us different from every other analysis tool.**

---

## 7. Analysis Tiers & Pricing

### Tier 1: **Lite Analysis** ($0.30-0.50 per security)
**Use Case:** Quick screening, intraday trading, high-volume analysis

**Components:**
- ✅ Technical analysis (Python - free)
- ✅ News summary (Haiku)
- ✅ Social sentiment (Haiku)
- ✅ Basic catalyst scan (Haiku)
- ❌ NO SEC filings
- ❌ NO earnings deep dive
- ❌ NO Opus synthesis

**Timeframes:** Intraday, Daily (for day traders)

**Output:** JSON + basic markdown summary

**Model Stack:**
- Haiku 4.5 only (~$0.30)
- 30-second analysis time

**Example Workflow:**
```python
def lite_analysis(symbol, csv_file):
    # Technical (free)
    technical = analyze_technical(csv_file)
    
    # Fundamental (Haiku only)
    news = haiku_summarize_news(symbol, days=7)
    sentiment = haiku_social_sentiment(symbol)
    catalysts = haiku_scan_catalysts(symbol)
    
    # Quick synthesis (Haiku)
    summary = haiku_quick_synthesis(technical, news, sentiment, catalysts)
    
    return {
        'technical': technical,
        'news': news,
        'sentiment': sentiment,
        'summary': summary
    }
```

---

### Tier 2: **Standard Analysis** ($1.50-3.00 per security)
**Use Case:** Swing trading, weekly analysis, position building

**Components:**
- ✅ Technical analysis (Python)
- ✅ News aggregation (Haiku)
- ✅ SEC filings (Sonnet)
- ✅ Earnings analysis (Sonnet)
- ✅ Social sentiment (Haiku)
- ✅ Catalyst extraction (Haiku)
- ✅ **Opus synthesis**

**Timeframes:** Daily, Weekly (for swing traders)

**Output:** Full markdown report + JSON + basic HTML

**Model Stack:**
- Haiku: News, sentiment, catalysts (~$0.30)
- Sonnet: SEC filings, earnings (~$1.00)
- Opus: Final synthesis (~$1.50)
- **Total: ~$2.80**

**Example Workflow:**
```python
def standard_analysis(symbol, csv_file):
    # Technical (free)
    technical = analyze_technical(csv_file)
    
    # Fundamental (Haiku + Sonnet)
    news = haiku_summarize_news(symbol, days=30)
    filings = sonnet_analyze_sec_filings(symbol)
    earnings = sonnet_analyze_earnings(symbol)
    sentiment = haiku_social_sentiment(symbol)
    catalysts = haiku_extract_catalysts(symbol)
    
    # Synthesis (Opus)
    thesis = opus_synthesize_thesis(
        technical, news, filings, earnings, sentiment, catalysts
    )
    
    # Report (Sonnet)
    report = sonnet_generate_report(thesis)
    
    return report
```

---

### Tier 3: **Premium Analysis** ($4.00-7.00 per security)
**Use Case:** Monthly analysis, high-conviction trades, portfolio allocation

**Components:**
- ✅ All Standard components
- ✅ Extended thinking (Opus + Sonnet)
- ✅ Multi-timeframe analysis (daily + weekly + monthly)
- ✅ Sector comparison
- ✅ Options flow analysis (if applicable)
- ✅ Macro overlay
- ✅ Multiple analysis passes for validation

**Timeframes:** Weekly, Monthly (for investors)

**Output:** Comprehensive report + interactive HTML dashboard

**Model Stack:**
- Haiku: High-volume tasks (~$0.40)
- Sonnet: Document analysis + extended thinking (~$2.00)
- Opus: Deep synthesis + extended thinking (~$3.50)
- **Total: ~$5.90**

**Additional Features:**
- Multi-timeframe confluence check
- Scenario analysis (best/base/worst case)
- Sector relative strength
- Historical pattern matching

**Example Workflow:**
```python
def premium_analysis(symbol, csv_file):
    # Multi-timeframe technical
    daily_tech = analyze_technical(csv_file_daily)
    weekly_tech = analyze_technical(csv_file_weekly)
    monthly_tech = analyze_technical(csv_file_monthly)
    
    # Deep fundamental (Sonnet with extended thinking)
    news = haiku_summarize_news(symbol, days=90)
    filings = sonnet_analyze_sec_filings_deep(symbol, extended_thinking=True)
    earnings = sonnet_analyze_earnings_deep(symbol, extended_thinking=True)
    sector = sonnet_sector_analysis(symbol)
    
    # Sentiment & catalysts
    sentiment = haiku_social_sentiment(symbol)
    catalysts = haiku_extract_catalysts(symbol, months=6)
    
    # Deep synthesis (Opus with extended thinking)
    thesis = opus_deep_synthesis(
        daily_tech, weekly_tech, monthly_tech,
        news, filings, earnings, sector, sentiment, catalysts,
        extended_thinking=True
    )
    
    # Scenario analysis (Opus)
    scenarios = opus_scenario_analysis(thesis)
    
    # Premium report (Sonnet)
    report = sonnet_generate_premium_report(thesis, scenarios)
    dashboard = generate_html_dashboard(report)
    
    return {
        'report': report,
        'dashboard': dashboard,
        'scenarios': scenarios
    }
```

---

### Tier 4: **Real-Time Analysis** (Premium feature)
**Use Case:** Active trading, real-time signals, algorithmic integration

**Components:**
- ✅ Streaming price data integration
- ✅ Real-time news alerts
- ✅ Ultra-fast Haiku-only mode
- ✅ WebSocket support
- ✅ Alert system

**Timeframes:** Intraday (1min, 5min, 15min)

**Output:** JSON stream + alerts

**Model Stack:**
- Haiku 4.5 only (for speed)
- ~$0.10-0.20 per analysis
- Sub-5-second latency

**Implementation:** Requires live data feed (separate cost)

---

## 6.3 Interactive Chat Interface (Critical New Feature)

**Purpose:** Transform static analysis into an interactive trading partner

This is a **game-changing differentiator** that elevates the system from "analysis tool" to "trading debate partner."

### Why This Matters

Traditional analysis tools give you a report. This system gives you a **sparring partner** who will:
- Challenge your assumptions
- Explore alternative scenarios
- Help you find blind spots
- Debate bull vs bear cases
- Stress-test your thesis before you risk capital

### Implementation Strategy

**Phase 1 (MVP): Claude.ai Integration**

The analyzer generates "discussion-ready" reports that can be uploaded directly to Claude.ai for interactive conversation.

**Report Format:**
```markdown
# WHR Analysis - Monthly Chart
## Generated: Feb 14, 2026

[Full technical + fundamental analysis here...]

---

## 🎯 INTERACTIVE DISCUSSION MODE

I have full access to this analysis. Ready to debate!

**Context Loaded:**
- Technical: 3 gaps, S/R levels, demand zone at $71-76
- Fundamental: Q4 earnings beat, housing concerns, margin pressure
- Bull case: MODERATE strength (4 supporting factors), target $112-115
- Bear case: STRONG (7 supporting factors), target $71-72
- User's thesis: 1 out of 9 criteria met (VERY WEAK setup)

**How to Use This:**
Ask me anything about this analysis:
- "Why is the $71 support critical?"
- "Challenge my bull case - where am I wrong?"
- "What if Fed cuts rates next month?"
- "What am I missing?"

I'll play devil's advocate and help you build conviction or recognize 
when to wait.

<analysis_data>
```json
{
  "symbol": "WHR",
  "price": 88.69,
  "gaps": [
    {"range": [115.45, 97.03], "status": "unfilled", "fill_potential": "high"}
  ],
  "support": [71.63, 77.35, 80.00],
  "resistance": [94.82, 100.00, 115.45],
  "bull_case": {
    "strength": "MODERATE",
    "supporting_factors": 4,
    "thesis": "Bounce from demand zone + earnings beat"
  },
  "bear_case": {
    "strength": "STRONG",
    "supporting_factors": 7,
    "thesis": "Below 200 SMA + housing weakness"
  },
  "user_thesis_score": "1/9 criteria met",
  ...
}
```
</analysis_data>
```

**User Flow:**
1. Run: `python main.py --symbol WHR --csv WHR.csv --tier standard`
2. Get markdown report with embedded context
3. Upload to Claude.ai (or paste into chat)
4. Discuss/debate using the analysis as shared context

### Example Debate Interactions

**Scenario 1: Challenging a Bull Thesis**
```
User: "I'm going long WHR at $88 based on this analysis"

Claude (Debate Mode):
"Let me challenge that. Three concerns:

1. BELOW 200 SMA: You're buying under the 200-day MA ($82.84). 
   Historically, buying below the 200-day MA on monthly charts 
   has lower success rates. Would you wait for $82.84 reclaim 
   as confirmation?

2. SETUP QUALITY: Your thesis only meets 1 out of 9 standard criteria. 
   The bear case has STRONG support (7 factors) while your entry 
   thesis has VERY WEAK support. Position sizing should reflect 
   this is not a high-quality setup.

3. CATALYST DEPENDENCY: Your thesis needs housing recovery. What 
   specific data will you monitor? At what point do you exit BEFORE 
   hitting your stop?

I'm not saying don't buy. I'm saying: let's build a better entry.
What if you:
- Wait for $82.84 breakout (better odds)
- Start 1/2 position here, add on $95 (confirmation)
- Set alerts for housing starts data

Which approach fits your conviction level?"
```

**Scenario 2: Stress Testing**
```
User: "What if the Fed cuts rates aggressively?"

Claude:
"Great scenario test. Let's map the implications:

**IF soft-landing cuts (economy healthy):**
- ✅ Lower rates → Housing demand ↑
- ✅ Consumer confidence ↑  
- ✅ WHR benefits from both
- Bull case strengthens: MODERATE → STRONG
- Would add 3+ supporting factors
- Target: $115 → $130

**IF panic cuts (recession fear):**
- ⚠️ Housing improves BUT high-end demand drops
- ⚠️ WHR's margins under pressure (luxury segment mix)
- ⚠️ Inventory issues if recession hits
- Bear case strengthens: STRONG → DOMINANT
- Would add 2+ contradicting factors  
- Target: $72 → $60

**Your action items:**
1. Monitor Fed meeting minutes - tone matters more than cut size
2. Track consumer confidence alongside rate moves
3. Have TWO playbooks ready based on cut reasoning

Want me to build out specific entry/exit rules for each scenario?"
```

**Scenario 3: Finding Blind Spots**
```
User: "What am I missing in this analysis?"

Claude:
"Here are 5 gaps I'd explore:

1. OPTIONS DATA: No implied volatility analysis. If IV >60th 
   percentile, market expects big moves. Validates breakout thesis 
   but means expensive option premiums.

2. SEASONALITY: Appliances peak in spring/summer. You're analyzing 
   Feb data. Pull 5-year seasonal pattern - does WHR typically 
   rally March-May?

3. INSIDER ACTIVITY: Recent insider buys at $88? Would massively 
   boost conviction. Selling? Red flag.

4. SECTOR FLOW: Is money moving INTO consumer discretionary or OUT? 
   Perfect setup + sector headwinds = mediocre returns.

5. CORRELATION: How does WHR move vs SPY? If market drops 10%, 
   does your $71 support hold? You might be betting on TWO things 
   (WHR + market stability).

**Before final decision, pull:**
- IV rank from options chain
- 5-year seasonality chart
- Insider trades last 90 days  
- XLY (consumer disc ETF) relative strength

Want help getting this data?"
```

### Model Selection for Chat

| Discussion Type | Model | Cost/Exchange | When to Use |
|----------------|-------|---------------|-------------|
| Quick questions | Haiku | $0.01-0.05 | "What's this level?" |
| Scenario analysis | Sonnet | $0.05-0.15 | "What if Fed cuts?" |
| Deep debate | Opus | $0.20-0.50 | "Challenge my thesis" |

**Typical Chat Session:**
- 10-20 exchanges
- Mix of Haiku (quick) + Sonnet (depth) + Opus (critical decisions)
- **Total cost: $1-4 per discussion session**

### Technical Implementation

**Key Functions:**
```python
def generate_discussion_report(analysis_results):
    """Generate markdown report with embedded context for Claude chat"""
    
    report = f"""
    # {symbol} Analysis - {timeframe}
    
    [Full analysis...]
    
    ---
    
    ## INTERACTIVE DISCUSSION MODE
    
    <analysis_data>
    ```json
    {json.dumps(analysis_results, indent=2)}
    ```
    </analysis_data>
    
    Ready to discuss! Ask me:
    - Challenge assumptions
    - Explore scenarios  
    - Find blind spots
    - Debate bull/bear cases
    """
    
    return report

def create_debate_prompts(thesis):
    """Generate counter-arguments and questions"""
    
    prompts = []
    
    # Technical challenges
    if thesis.price < thesis.ma_200:
        prompts.append(
            "Price is below 200 SMA - low probability long setup. "
            "Would you wait for MA reclaim?"
        )
    
    # Probability challenges  
    if thesis.bull_probability < 0.60:
        prompts.append(
            f"Bull case only {thesis.bull_probability:.0%} probable. "
            "How does this affect position sizing?"
        )
    
    return prompts
```

### Benefits

1. **Pressure-Test Ideas:** Find flaws before risking capital
2. **Build Conviction:** Solid thesis survives scrutiny
3. **Learn:** Understand WHY certain levels matter
4. **Save Time:** Faster than researching edge cases alone
5. **Decision Quality:** Better entries, exits, and risk management

### Implementation Priority: **CRITICAL**

This feature is what transforms the project from "yet another analysis tool" into a genuine trading partner. It's the moat.

### Phase 2 (Future): API-Based Chat Interface

Build custom chat interface with:
- Conversation history
- Streaming responses
- Model switching
- Cost tracking
- Save/resume discussions

**Technology Stack:**
- FastAPI for backend
- WebSockets for streaming
- React for frontend
- Redis for conversation state

**Estimated effort:** 2-3 weeks after MVP

---

## 7. Implementation Plan

---

## 8. Agentic Workflow Architecture

### Multi-Agent System Design

```
USER REQUEST
     ↓
[ORCHESTRATOR AGENT]
     ↓
     ├─→ [DATA AGENT]
     │   ├─ Parse CSV
     │   ├─ Fetch news
     │   ├─ Get SEC filings
     │   └─ Collect social data
     │
     ├─→ [ANALYSIS AGENTS] (Parallel)
     │   ├─ Technical Agent (Python)
     │   ├─ News Agent (Haiku)
     │   ├─ Fundamental Agent (Sonnet)
     │   └─ Sentiment Agent (Haiku)
     │
     ├─→ [SYNTHESIS AGENT] (Opus)
     │   └─ Combine all signals
     │
     └─→ [REPORT AGENT] (Sonnet)
         └─ Generate outputs
```

### Agent Roles:

**1. Orchestrator Agent**
- Determines analysis tier
- Routes tasks to appropriate agents
- Manages parallel execution
- Handles errors and retries

**2. Data Agent**
- Fetches all external data
- Caches results
- Validates data quality

**3. Technical Analysis Agent**
- Pure Python execution
- No LLM calls
- Fast and deterministic

**4. News Agent (Haiku)**
- Summarizes news
- Extracts sentiment
- Identifies catalysts

**5. Fundamental Agent (Sonnet)**
- Analyzes SEC filings
- Processes earnings
- Deep document analysis

**6. Sentiment Agent (Haiku)**
- Social media analysis
- Retail sentiment gauge

**7. Synthesis Agent (Opus)**
- Combines all inputs
- Generates bull/bear thesis
- Calculates risk/reward

**8. Report Agent (Sonnet)**
- Formats outputs
- Generates markdown/JSON/HTML

---

### Agentic Workflow Example (Claude Code Integration)

```python
# main.py - Agentic orchestrator

from anthropic import Anthropic
import asyncio

class TradingAnalysisOrchestrator:
    def __init__(self, tier="standard"):
        self.tier = tier
        self.client = Anthropic()
        
    async def analyze(self, symbol, csv_file):
        # Step 1: Data collection (parallel)
        data_tasks = [
            self.parse_csv(csv_file),
            self.fetch_news(symbol),
            self.fetch_filings(symbol),
            self.fetch_social(symbol)
        ]
        
        csv_data, news, filings, social = await asyncio.gather(*data_tasks)
        
        # Step 2: Analysis (parallel)
        analysis_tasks = [
            self.technical_analysis(csv_data),
            self.news_analysis(news),  # Haiku
            self.fundamental_analysis(filings),  # Sonnet
            self.sentiment_analysis(social)  # Haiku
        ]
        
        technical, news_insights, fundamental, sentiment = await asyncio.gather(*analysis_tasks)
        
        # Step 3: Synthesis (Opus - sequential)
        if self.tier in ["standard", "premium"]:
            thesis = await self.synthesize_opus(
                technical, news_insights, fundamental, sentiment
            )
        else:
            thesis = await self.synthesize_haiku(
                technical, news_insights, sentiment
            )
        
        # Step 4: Report generation
        report = await self.generate_report(thesis)
        
        return report
    
    async def synthesize_opus(self, *inputs):
        # Call Opus 4.6 for synthesis
        response = self.client.messages.create(
            model="claude-opus-4-6-20260205",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": self._build_synthesis_prompt(*inputs)
            }]
        )
        return response.content[0].text
```

---

## 9. Implementation Phases

### **Phase 1: MVP (Week 1-2)**
**Goal:** Basic end-to-end workflow with Sonnet 4.5 only

**Deliverables:**
- CSV parser
- Basic technical analysis (gaps, S/R)
- News aggregation (Sonnet)
- Simple synthesis (Sonnet)
- Markdown report output

**Cost per analysis:** ~$1.00

**Success criteria:**
- Analyze 1 security in <60 seconds
- Generate readable markdown report
- Identify top 3 gaps and S/R levels

---

### **Phase 2: Multi-Model Orchestration (Week 3-4)**
**Goal:** Add Haiku and Opus, implement tiered analysis

**Deliverables:**
- Tier system (Lite/Standard/Premium)
- Haiku for news/sentiment
- Opus for synthesis
- Parallel execution
- Cost tracking per analysis

**Cost per analysis:**
- Lite: $0.50
- Standard: $3.00
- Premium: $6.00

**Success criteria:**
- 3x speed improvement (parallel execution)
- 60% cost reduction for Lite tier
- Improved synthesis quality (Opus vs Sonnet)

---

### **Phase 3: Asset Class Expansion (Week 5-6)**
**Goal:** Support Stocks, Crypto, Futures, Options

**Deliverables:**
- Asset-specific modules
- Options flow analysis
- Crypto on-chain metrics
- Futures COT data
- Sector-specific catalysts

**Success criteria:**
- Successfully analyze BTC, ES futures, SPY options
- Asset-specific insights in reports

---

### **Phase 4: Advanced Features (Week 7-8)**
**Goal:** Extended thinking, multi-timeframe, batch processing

**Deliverables:**
- Extended thinking integration
- Multi-timeframe analysis
- Batch API support (50% discount)
- Prompt caching (90% cost reduction on repeated analyses)
- HTML dashboard

**Cost optimization:**
- Batch mode: ~$1.50 per analysis (vs $3.00)
- Cached re-analysis: ~$0.30 (vs $3.00)

---

### **Phase 5: Real-Time & Automation (Week 9-10)**
**Goal:** Real-time data, alerts, scheduling

**Deliverables:**
- Live data integration
- Alert system (price levels, catalyst triggers)
- Scheduled analysis (cron jobs)
- API endpoint (optional)

---

### **Phase 6: Polish & Scale (Week 11-12)**
**Goal:** Production-ready, documentation, error handling

**Deliverables:**
- Comprehensive documentation
- Error handling and retries
- Logging and monitoring
- Cost dashboard
- User configuration file

---

## 10. Technology Stack

### **Core**
- **Language:** Python 3.11+
- **Data Processing:** pandas, numpy
- **LLM Integration:** anthropic SDK
- **Async:** asyncio, aiohttp
- **Configuration:** YAML/JSON config files

### **Data Sources**
- **News:** NewsAPI, Alpha Vantage, web scraping
- **SEC Filings:** SEC EDGAR API
- **Social:** Reddit API (PRAW), Twitter API
- **Economic:** FRED API, economic calendar APIs
- **Market Data:** yfinance (supplementary)

### **Optional Dependencies**
- **TA-Lib:** Advanced technical indicators
- **Plotly:** Interactive charts for HTML dashboard
- **FastAPI:** If building API endpoint
- **Redis:** Caching layer for production

### **Development Tools**
- **Claude Code:** Agentic coding assistance
- **Git:** Version control
- **pytest:** Testing framework
- **Black:** Code formatting

---

## 11. File Structure

```
trading-analyzer/
├── README.md
├── PRD.md (this document)
├── config/
│   ├── config.yaml              # Main configuration
│   ├── api_keys.yaml            # API keys (gitignored)
│   └── tier_profiles.yaml       # Analysis tier definitions
│
├── src/
│   ├── main.py                  # Entry point
│   ├── orchestrator.py          # Agentic workflow coordinator
│   │
│   ├── agents/
│   │   ├── data_agent.py        # Data fetching
│   │   ├── technical_agent.py   # Technical analysis
│   │   ├── news_agent.py        # News (Haiku)
│   │   ├── fundamental_agent.py # SEC/Earnings (Sonnet)
│   │   ├── sentiment_agent.py   # Social (Haiku)
│   │   ├── synthesis_agent.py   # Bull/Bear (Opus)
│   │   └── report_agent.py      # Report generation (Sonnet)
│   │
│   ├── parsers/
│   │   ├── csv_parser.py        # TradingView CSV
│   │   ├── sec_parser.py        # SEC filings
│   │   └── earnings_parser.py   # Earnings transcripts
│   │
│   ├── analyzers/
│   │   ├── gap_analyzer.py      # Gap detection
│   │   ├── sr_calculator.py     # Support/Resistance
│   │   ├── supply_demand.py     # Supply/Demand zones
│   │   └── indicators.py        # Technical indicators
│   │
│   ├── models/
│   │   ├── haiku_model.py       # Haiku wrapper
│   │   ├── sonnet_model.py      # Sonnet wrapper
│   │   └── opus_model.py        # Opus wrapper
│   │
│   ├── outputs/
│   │   ├── markdown_generator.py
│   │   ├── json_generator.py
│   │   └── html_generator.py
│   │
│   └── utils/
│       ├── cache.py             # Caching logic
│       ├── logger.py            # Logging
│       ├── cost_tracker.py      # Cost monitoring
│       └── validators.py        # Data validation
│
├── data/
│   ├── cache/                   # Cached API responses
│   ├── reports/                 # Generated reports
│   └── samples/                 # Sample CSVs
│
├── tests/
│   ├── test_parsers.py
│   ├── test_analyzers.py
│   └── test_agents.py
│
└── requirements.txt
```

---

## 12. Configuration Files

### config.yaml
```yaml
# Analysis Tier (lite/standard/premium/realtime)
tier: standard

# Asset Class (stock/crypto/futures/options)
asset_class: stock

# Timeframe (intraday/daily/weekly/monthly)
timeframe: daily

# Model Configuration
models:
  haiku:
    model_id: "claude-haiku-4-5-20251001"
    max_tokens: 4000
    temperature: 0.3
  
  sonnet:
    model_id: "claude-sonnet-4-5-20250929"
    max_tokens: 8000
    temperature: 0.3
    extended_thinking: false
  
  opus:
    model_id: "claude-opus-4-6-20260205"
    max_tokens: 16000
    temperature: 0.3
    extended_thinking: true

# Data Sources
data_sources:
  news:
    enabled: true
    sources: [newsapi, alpha_vantage]
    lookback_days: 30
  
  sec_filings:
    enabled: true
    filing_types: [10-Q, 10-K, 8-K]
  
  social:
    enabled: true
    platforms: [reddit, twitter]
    lookback_days: 7

# Output Configuration
outputs:
  formats: [markdown, json, html, pdf]  # PDF export added
  save_to_disk: true
  output_dir: ./data/reports
  
  # PDF settings
  pdf:
    engine: pdfkit  # 'pdfkit' (HTML→PDF) or 'reportlab' (custom)
    include_charts: true
    page_size: letter  # letter, a4

# Cost Management
cost_management:
  max_cost_per_analysis: 10.00
  use_prompt_caching: true
  use_batch_api: false

# Technical Analysis
technical:
  gap_threshold_pct: 2.0
  sr_sensitivity: medium
  lookback_bars: 100
```

---

## 13. Example Usage

### Command Line Interface

```bash
# Basic usage
python main.py --symbol WHR --csv NYSE_WHR__1M_5f55d.csv --tier standard

# Lite analysis (fast/cheap)
python main.py --symbol AAPL --csv AAPL_daily.csv --tier lite

# Premium with extended thinking
python main.py --symbol TSLA --csv TSLA_weekly.csv --tier premium --extended-thinking

# Batch analysis
python main.py --batch watchlist.txt --tier standard --output batch_results/

# Real-time mode
python main.py --symbol SPY --realtime --interval 5min
```

### Python API

```python
from src.orchestrator import TradingAnalysisOrchestrator

# Initialize
analyzer = TradingAnalysisOrchestrator(tier="standard")

# Analyze single security
report = await analyzer.analyze(
    symbol="WHR",
    csv_file="NYSE_WHR__1M_5f55d.csv",
    timeframe="monthly"
)

print(report.markdown)
print(f"Cost: ${report.cost:.2f}")

# Batch analysis
symbols = ["WHR", "AAPL", "TSLA", "NVDA"]
results = await analyzer.batch_analyze(symbols, tier="lite")

# Get cost summary
print(analyzer.get_cost_summary())
```

---

## 14. Open Questions & Decisions Needed

### Technical Decisions:
1. **Caching Strategy:**
   - How long to cache SEC filings? (Recommendation: 90 days)
   - Cache news articles? (Recommendation: 24 hours)

2. **Rate Limiting:**
   - Max API calls per minute? (Anthropic limits)
   - Retry logic for failed calls?

3. **Error Handling:**
   - What to do if SEC filing not found? (Skip or retry?)
   - Fallback if LLM call fails? (Use cached or simplified analysis?)

### Product Decisions:
1. **Batch Processing:**
   - Build batch mode in Phase 2 or Phase 4?
   - Auto-use batch API for >5 securities?

2. **Real-Time:**
   - Offer as separate product or tier?
   - Pricing model for real-time?

3. **Sharing:**
   - Allow users to share reports publicly?
   - Social features (community watchlists)?

### Cost Management:
1. **Budget Caps:**
   - Hard cap per analysis? Per day?
   - Warning at 80% of budget?

2. **Optimization:**
   - Auto-downgrade to cheaper tier if budget hit?
   - Queue system for batch processing?

---

## 15. Success Metrics

### Performance Metrics:
- **Latency:** <60s for Standard, <10s for Lite, <300s for Premium
- **Accuracy:** 90% of technical levels within ±0.5% of manual analysis
- **Cost:** Actual cost within ±20% of projected cost per tier

### Quality Metrics:
- **Relevance:** News/catalysts rated >7/10 relevance by users
- **Actionability:** Users can make trade decisions from report alone
- **Synthesis Quality:** Bull/bear cases logically consistent with data

### Business Metrics (if productized):
- **User Adoption:** 100 users in first month
- **Retention:** 70% monthly retention
- **Cost per User:** <$50/month average
- **Premium Conversion:** 30% of users upgrade to Premium tier

---

## 16. Risk Analysis

### Technical Risks:
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limits hit | High | Medium | Implement retry logic, caching |
| LLM hallucination on filings | High | Low | Multi-pass validation, user warnings |
| CSV format changes | Medium | Medium | Robust parser with validation |
| Cost overruns | High | Medium | Hard caps, cost tracking, alerts |

### Product Risks:
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users prefer manual analysis | High | Low | Emphasize time savings, quality |
| Competitors copy approach | Medium | High | Focus on quality, speed of iteration |
| Regulatory concerns (not investment advice) | High | Low | Clear disclaimers in all outputs |

---

## 17. Appendix

### A. Sample Outputs

*See separate document: sample_outputs.md*

### B. API Documentation

*See separate document: api_docs.md*

### C. Cost Calculator

*See separate document: cost_calculator.xlsx*

### D. Example Reports

*See `/examples` directory for:*
- `WHR_monthly_standard.md`
- `AAPL_daily_lite.json`
- `TSLA_weekly_premium.html`

---

## Document Control

**Version:** 1.1  
**Last Updated:** February 14, 2026  
**Next Review:** March 14, 2026  
**Approval:** Pending

**Changelog:**

**v1.1 (Feb 14, 2026) - Evidence Scorecard + Checklist Method Update:**
- ✅ Added **Component 0: Conviction Check** - Pre-analysis thesis capture from user
- ✅ Enhanced **Component 9: Catalyst Extractor** with "What Needs to Happen" framework
  - Bull/bear scenario triggers with specific thresholds
  - Algorithmic trading triggers (keywords, metrics)
  - Leading indicators to watch before catalysts
- ✅ Enhanced **Component 10: Synthesis Engine** with Evidence Scorecard methodology
  - NO FAKE PERCENTAGES - uses evidence ratios instead
  - Transparent assessment (STRONG/MODERATE/WEAK/VERY WEAK)
- ✅ Completely rewrote **Component 12: Thesis Validation Framework**
  - Evidence Scorecard (quick visual summary)
  - Quality Checklist (detailed criterion-by-criterion evaluation)
  - 5 thesis-specific checklists defined (Support Bounce, Breakout, Gap Fill, Earnings, Options Flow)
  - Complete Python implementation specifications
- ✅ Enhanced **Component 11: Report Generator**
  - Added Evidence Scorecard section to markdown template
  - Added detailed Quality Checklist section
  - Added PDF export capability (pdfkit + reportlab)
  - Enhanced Interactive Discussion Mode format
- ✅ Updated **Section 4.1: Data Inputs** with specific API providers
  - MVP (Free): yfinance, TD Ameritrade, SEC EDGAR, Reddit, FRED - **$0/month**
  - Phase 2: Add Unusual Whales Pro ($39/mo)
  - Phase 3: Add Polygon.io ($99/mo) for real-time
  - Enterprise: Add sec-api.io ($99/mo)
- ✅ Updated **Section 4.2: Data Outputs** to include PDF format
- ✅ Updated **Section 4.4: Dependencies** with complete requirements.txt
  - Added PDF libraries (pdfkit, reportlab)
  - Added all API client libraries
  - Separated MVP (free) from production (paid) dependencies

**Key Philosophy Changes:**
- **No Fake Percentages:** Never use unsupported probability claims
- **Transparent Methodology:** Show exactly how assessments are made
- **User Accountability:** Force thesis articulation before analysis
- **Evidence-Based:** Count factors, don't invent probabilities
- **Constructive Challenge:** Help users see weaknesses in their thesis

**v1.0 (Feb 14, 2026):** Initial PRD with multi-model orchestration, tiered analysis, agentic workflow

---

**End of PRD**