# Changelog

All notable changes to the Trading Analyzer backend.

Format: each entry explains **what** changed and **why** it was needed.

---

## 2026-02-19 — Multi-Timeframe S/R Confluence

**Commit:** `b3fe5b1`

### What changed
- `sr_calculator.py`: `SRLevel` now carries `timeframe`, `is_confluence`, and `confluence_timeframes` fields. New `detect_confluence()` function merges levels within 0.5% across different timeframes into a single boosted-strength level. `summarize_levels()` splits output into `key_levels` (confluence or strength >= 8) and `minor_levels`. Round-number generation restricted to daily/default timeframes only.
- `orchestrator.py`: `_step_technical_analysis()` fetches daily (3-month) and weekly (6-month) candles via yfinance when a ticker symbol is available, runs S/R on each timeframe, then calls `detect_confluence()` to merge.
- `yfinance_fetcher.py`: New `fetch_sr_timeframes(ticker)` returns `{"daily": df, "weekly": df}`.
- Tests: 21 new tests across analyzers, orchestrator, and stock fetcher covering confluence merging, timeframe tagging, key/minor split, and the new fetcher.

### Why
Single-timeframe S/R is noisy. A support level at $252 on the daily chart that also appears at $252.30 on the weekly chart is far more significant than either alone. Multi-timeframe confluence is how professional traders filter signal from noise. By merging nearby levels across timeframes and flagging them as "key", the frontend can highlight the levels that actually matter and relegate the rest to a secondary view.

---

## 2026-02-17 — Parallel Agent Execution

**Commit:** `eeabf1f`

### What changed
- `orchestrator.py`: News and fundamental agents now run concurrently using `ThreadPoolExecutor(max_workers=2)`. Each agent writes to a separate key in the result dict, so no locking is needed.

### Why
News (Haiku + web_search) and fundamental (SEC fetch + Sonnet) are independent and I/O-bound. Running them sequentially added ~30s to standard-tier analysis. Parallelizing cuts wall-clock time by roughly half for those steps.

---

## 2026-02-17 — CSV Prompt Injection Sanitization

**Commit:** `d455451`

### What changed
- New `src/utils/sanitize.py` with `sanitize_dataframe()` and `sanitize_ticker()`.
- Column names checked against an allowlist of OHLCV and indicator patterns; unknown columns renamed to `extra_col_N`.
- Non-date columns coerced to numeric (text becomes NaN). Columns >90% NaN after coercion are dropped.
- Strings >20 chars in numeric columns trigger security warnings.
- Integrated into `csv_parser._parse_dataframe()` after column normalization.

### Why
Users upload arbitrary CSVs. A malicious CSV could embed prompt-injection payloads in column names or cell values that later get passed to Claude agents as context. Sanitizing at the parser level ensures only numeric data reaches the LLM pipeline.

---

## 2026-02-17 — Fix CSV Ticker Extraction

**Commit:** `88d0a44`

### What changed
- `api.py`: Replaced inline `filename.split("_")[0]` logic with `_extract_symbol()` from csv_parser.
- Ticker sanitized to letters and dots only, max 10 chars.

### Why
The old logic returned "NYSE" for a file named `NYSE_WHR__1M.csv` because it split on `_` and took index 0. The csv_parser already had `_extract_symbol()` that correctly strips exchange prefixes and timeframe suffixes.

---

## 2026-02-16 — Two-Level Supabase Caching

**Commit:** `794b02a`

### What changed
- L1 cache: `sec_filings_cache` stores raw SEC filing text (365-day TTL).
- L2 cache: `fundamental_analyses_cache` stores Claude analysis results (90-day TTL).
- Cache flow: check L2 -> check L1 -> fetch from SEC -> analyze with Claude -> save both.
- Gracefully disabled when `SUPABASE_URL`/`SUPABASE_KEY` env vars are not set.

### Why
SEC filings don't change once published, but fetching + parsing them takes ~2s and analyzing with Sonnet costs ~$0.08. Caching the raw filing avoids re-fetching and caching the analysis avoids re-spending on Claude. Cached hits return in ~0.1s at $0 cost. Two levels because the filing text is reusable even when the analysis prompt changes.

---

## 2026-02-16 — Parallel SEC Filing Fetch for International Companies

**Commit:** `4abd939`

### What changed
- `sec_fetcher.py`: New `fetch_filing_parallel()` tries US (10-K/10-Q) and foreign (20-F/6-K) filing types simultaneously using ThreadPoolExecutor.
- `filing_period` param flows through API -> orchestrator -> agent.

### Why
Foreign companies like BABA and TSM file 20-F/6-K instead of 10-K/10-Q with the SEC. Previously the system only looked for US filing types, returning nothing for international tickers. Fetching both in parallel means no extra latency — whichever exists gets returned.

---

## 2026-02-15 — API Hardening

**Commits:** `f3f712e`, `d1c7394`

### What changed
- CORS: Origins read from `ALLOWED_ORIGINS` env var, defaults to localhost dev ports.
- Cache DELETE endpoints require `X-Admin-Secret` header (`ADMIN_SECRET` env).
- Rate limiting: `/analyze/full` (10/min), `/analyze` (30/min) via slowapi. Disabled with `RATE_LIMIT_ENABLED=false` for tests.
- `/health` endpoint hides API key prefix, SDK versions, and tracebacks unless `DEBUG_HEALTH=true`.

### Why
The API is publicly accessible on Railway. Without CORS restrictions, any origin could call it. Without rate limiting, a single client could exhaust Anthropic API budget. Without admin auth on cache endpoints, anyone could wipe cached analyses. The health endpoint was leaking internal details (key prefixes, SDK versions) that could help an attacker.

---

## 2026-02-15 — Frontend Compatibility Fixes

**Commits:** `f53fb0e`, `532d617`

### What changed
- `/config/tiers` now returns a raw JSON array (not `{"tiers": [...]}`) and uses `"label"` key instead of `"name"`.
- Ticker validation regex changed from `isalpha()` to `[A-Z0-9.]{1,6}`.

### Why
The frontend expected `Array.isArray(data)` and looked for a `"label"` field — the backend was returning a wrapped object with `"name"`. Tickers like `BRK.B` and `BRK.A` were rejected because `isalpha()` doesn't allow dots or digits.
