# Multi-Asset Trading Analysis System
## AI-Powered Technical & Fundamental Analysis

**Status:** MVP Complete
**Version:** 0.1.0
**Last Updated:** February 14, 2026

---

## What Is This?

A trading analysis system that combines:
- **Technical Analysis** (gaps, S/R levels, supply/demand zones)
- **Fundamental Analysis** (SEC filings via EDGAR)
- **News & Sentiment** (RSS feeds + Haiku summarization)
- **Multi-Model AI Orchestration** (Haiku, Sonnet, Opus working together)
- **Evidence Scorecard Method** (no fake percentages)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API keys
cp config/api_keys.yaml.example config/api_keys.yaml
# Edit api_keys.yaml with your Anthropic API key

# Run analysis (CLI)
python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --tier standard

# Output formats
python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --format markdown
python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --format html -o report.html
python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --format json -o report.json

# Lite tier (fast, cheap — Haiku only)
python -m src.main --symbol WHR --csv data/samples/NYSE_WHR__1M.csv --tier lite
```

### API Server

```bash
# Start the FastAPI server
uvicorn api:app --reload

# Endpoints:
# GET  /health           - Health check
# GET  /tiers            - List analysis tiers
# POST /analyze          - Technical analysis (CSV upload)
# POST /analyze/full     - Full AI analysis (CSV + symbol + tier + format)
# POST /analyze/gaps     - Gap analysis only
# POST /analyze/levels   - S/R levels only
# POST /analyze/zones    - Supply/demand zones only
```

---

## Analysis Tiers

| Tier | Models | Includes | Max Cost |
|------|--------|----------|----------|
| **Lite** | Haiku | Technical + News | $0.50 |
| **Standard** | Haiku + Sonnet + Opus | Technical + News + SEC + Synthesis | $3.00 |
| **Premium** | All + Extended Thinking | Same as Standard with deeper analysis | $7.00 |

---

## Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| **Markdown** | Clean text report | Upload to Claude.ai for discussion |
| **JSON** | Structured data | API integration, further processing |
| **HTML** | Standalone dashboard | Browser viewing, dark/light themes |

See `data/reports/` for example outputs.

---

## Architecture

```
CSV File → Parser → Technical Analysis (free)
                  → News Agent (Haiku — fast & cheap)
                  → SEC Agent (Sonnet — balanced)
                  → Synthesis Agent (Opus — deep reasoning)
                  → Report Generator (Markdown/JSON/HTML)
```

### Project Structure

```
src/
├── parsers/         CSV parsing and validation
├── analyzers/       Gap detection, S/R levels, supply/demand zones
├── agents/          AI model wrappers + specialized agents
│   ├── model_wrappers.py   Haiku/Sonnet/Opus API wrappers
│   ├── news_agent.py       Haiku-powered news analysis
│   ├── fundamental_agent.py Sonnet-powered SEC filing analysis
│   └── synthesis_agent.py  Opus-powered bull/bear synthesis
├── outputs/         Report generators (Markdown, JSON, HTML)
├── utils/           Cost tracking, config, logging, SEC fetcher
├── orchestrator.py  Pipeline coordinator
└── main.py          CLI entry point

tests/               266 unit tests + 7 integration tests
api.py               FastAPI backend
```

---

## Testing

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src

# Run real API integration tests (costs money!)
python -m pytest tests/test_integration_real.py -v -m integration
```

---

## Cost Structure

Typical analysis costs:
- **Lite:** ~$0.001 (Haiku only)
- **Standard:** ~$0.16 (Haiku + Sonnet + Opus)
- **Premium:** ~$0.23 (with extended thinking)

All well within tier budgets. Cost tracking is built into every API call.

---

## Disclaimers

- Not financial advice
- Educational purposes only
- Trading involves risk of loss
- Verify all data independently
- AI can make mistakes

---

**Built with Claude**
