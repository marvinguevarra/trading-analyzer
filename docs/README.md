# Multi-Asset Trading Analysis System
## AI-Powered Technical & Fundamental Analysis with Interactive Debate Mode

**Status:** In Development  
**Version:** 0.1.0  
**Last Updated:** February 14, 2026

---

## 🎯 What Is This?

A sophisticated trading analysis system that combines:
- **Technical Analysis** (gaps, S/R, supply/demand zones)
- **Fundamental Analysis** (SEC filings, earnings, news, social sentiment)
- **Multi-Model AI Orchestration** (Haiku, Sonnet, Opus working together)
- **Interactive Debate Mode** (discuss and challenge your ideas with Claude)

### The Game-Changer: Interactive Sparring

Unlike traditional tools that just give you a report, this system becomes your **trading debate partner**:
- Challenges your assumptions
- Plays devil's advocate on trade ideas
- Explores "what if" scenarios
- Helps you find blind spots
- Tests your conviction before you risk capital

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API keys
cp config/api_keys.yaml.example config/api_keys.yaml
# Edit api_keys.yaml with your Anthropic API key

# Run analysis
python main.py --symbol WHR --csv data/NYSE_WHR__1M.csv --tier standard

# Get interactive report
# Upload the generated markdown to Claude.ai and start discussing!
```

---

## 💰 Cost Structure

### Analysis Tiers

| Tier | Use Case | Cost/Security | Speed |
|------|----------|---------------|-------|
| **Lite** | Intraday/scalping | $0.10-0.30 | <10s |
| **Standard** | Daily swings | $0.80-2.00 | 30-60s |
| **Premium** | Weekly/monthly | $3.00-7.00 | 2-5min |
| **Real-Time** | Active trading | $0.20/signal | <5s |

---

## 💬 Interactive Discussion Mode - THE KILLER FEATURE

After analysis, upload the report to Claude.ai and have a real conversation:

```
User: "I think this is a buy at $88"

Claude: "Let me challenge that. You're buying BELOW the 200 SMA. 
Historically <40% win rate. Would you wait for confirmation?

Also, bull case is only 45% probable. How does this affect sizing?"

User: "What if Fed cuts rates?"

Claude: "Great scenario test. Two outcomes:
- Soft landing: Bull case → 65%, target $130
- Recession: Bear case → 55%, target $60

You need TWO playbooks. Want me to build specific rules for each?"
```

---

## 🏗️ Architecture

### Multi-Model Orchestration

```
Python → Technical Analysis (free)
Haiku → News & Sentiment (fast & cheap)
Sonnet → SEC Filings & Earnings (balanced)
Opus → Final Synthesis & Debate (deep reasoning)
```

**See PRD.md for full architecture details.**

---

## 📊 Example: WHR Monthly Analysis

**Cost:** ~$3.00  
**Time:** 2-3 minutes

**Technical (Python - $0):**
- Gap: $115.45 → $97.03 (78% fill probability)
- Support: $71.63, $77.35, $80.00
- Resistance: $94.82, $100.00, $115.45

**Fundamental (Sonnet - $1.20):**
- Q4 earnings beat but guidance lowered
- Margin pressure from tariffs
- Mixed news sentiment

**Synthesis (Opus - $1.50):**
- Bull case: 45% → Target $112-115
- Bear case: 35% → Target $71-72
- Recommendation: WAIT for $82.84 reclaim

---

## 📈 Roadmap

### Phase 1: MVP (4 weeks)
- Core technical analysis
- CSV parser
- News aggregator (Haiku)
- Basic synthesis (Sonnet)
- Interactive chat format

### Phase 2: Enhanced (6 weeks)
- SEC filing parser
- Earnings analyzer
- Social sentiment
- Deep synthesis (Opus)
- HTML dashboards

### Phase 3: Advanced (8 weeks)
- Real-time mode
- Batch analysis
- Options analysis
- Crypto metrics
- Backtesting

---

## 💡 Philosophy: Why Multi-Model?

**Right tool for the right job:**
- Haiku = Speed & volume (news, social)
- Sonnet = Quality & structure (SEC, earnings)
- Opus = Critical thinking (synthesis, debate)

**Result:** Optimal cost/quality vs. using one model for everything

---

## 🎯 Supported Asset Classes

- ✅ US Stocks
- ✅ Crypto
- ✅ Futures/Commodities
- ✅ Options

---

## ⚠️ Disclaimers

- Not financial advice
- Educational purposes only
- Trading involves risk of loss
- Verify all data independently
- AI can make mistakes

---

## 📚 Documentation

- **PRD.md** - Complete product requirements
- **docs/** - Detailed documentation
- **examples/** - Sample reports

---

**Built with Claude Sonnet 4.5**
