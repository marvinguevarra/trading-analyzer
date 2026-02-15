"""FastAPI backend for Trading Analyzer.

Endpoints:
  GET  /health              - Health check
  GET  /                    - API info
  POST /analyze             - Full technical analysis (CSV upload)
  POST /analyze/full        - Complete AI-powered analysis (CSV + AI agents)
  POST /analyze/gaps        - Gap analysis only
  POST /analyze/levels      - Support/Resistance only
  POST /analyze/zones       - Supply/Demand zones only
  GET  /analyze/sample/{name} - Analyze a bundled sample file
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from src.parsers.csv_parser import ParsedData, load_csv
from src.analyzers.gap_analyzer import detect_gaps, summarize_gaps
from src.analyzers.sr_calculator import calculate_levels, summarize_levels
from src.analyzers.supply_demand import identify_zones, summarize_zones
from src.orchestrator import TradingAnalysisOrchestrator
from src.utils.tier_config import list_tiers

app = FastAPI(
    title="Trading Analyzer API",
    description="Multi-asset trading analysis — gaps, S/R levels, supply/demand zones. No fake percentages.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLES_DIR = Path(__file__).parent / "data" / "samples"


# ── Helpers ──────────────────────────────────────────────────


def _sanitize(obj):
    """Recursively convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _parse_upload(file_bytes: bytes, filename: str) -> ParsedData:
    """Save uploaded bytes to a temp file and parse with csv_parser."""
    suffix = Path(filename).suffix or ".csv"
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, prefix=Path(filename).stem + "_"
    ) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return load_csv(tmp_path)
    finally:
        os.unlink(tmp_path)


def _metadata(parsed: ParsedData) -> dict:
    """Extract serializable metadata from ParsedData."""
    return {
        "symbol": parsed.symbol,
        "timeframe": parsed.timeframe,
        "bars": parsed.bar_count,
        "date_range": list(parsed.date_range),
        "indicators": parsed.indicators,
        "quality": {
            "score": round(parsed.quality.score, 3),
            "is_valid": parsed.quality.is_valid,
            "errors": parsed.quality.errors,
            "warnings": parsed.quality.warnings,
        },
    }


def _run_full_analysis(parsed: ParsedData, min_gap_pct: float) -> dict:
    """Run all three analyzers and return combined results."""
    df = parsed.df
    current_price = float(df["close"].iloc[-1])

    gaps = detect_gaps(df, min_gap_pct=min_gap_pct)
    levels = calculate_levels(df, current_price=current_price)
    zones = identify_zones(df)

    return _sanitize({
        "metadata": _metadata(parsed),
        "current_price": round(current_price, 2),
        "gaps": summarize_gaps(gaps),
        "support_resistance": summarize_levels(levels, current_price),
        "supply_demand": summarize_zones(zones, current_price),
    })


# ── Routes ───────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "name": "Trading Analyzer API",
        "version": "0.1.0",
        "endpoints": [
            "GET  /health",
            "GET  /tiers",
            "POST /analyze",
            "POST /analyze/full",
            "POST /analyze/gaps",
            "POST /analyze/levels",
            "POST /analyze/zones",
            "GET  /analyze/sample/{filename}",
        ],
    }


@app.get("/health")
async def health():
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    key_prefix = os.environ.get("ANTHROPIC_API_KEY", "")[:10] + "..." if has_key else None

    # Test actual Haiku call
    api_test = "skipped"
    debug_info = {}
    if has_key:
        try:
            import anthropic as anth
            import httpx
            import traceback as tb
            import ssl

            debug_info["anthropic_version"] = anth.__version__
            debug_info["httpx_version"] = httpx.__version__

            # Check SSL
            try:
                ctx = ssl.create_default_context()
                debug_info["ssl_ok"] = True
            except Exception as ssl_e:
                debug_info["ssl_ok"] = False
                debug_info["ssl_error"] = str(ssl_e)

            # Raw httpx POST test (like the SDK would do)
            try:
                raw_resp = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 8,
                        "messages": [{"role": "user", "content": "Reply: OK"}],
                    },
                    timeout=15.0,
                )
                debug_info["raw_httpx_status"] = raw_resp.status_code
                debug_info["raw_httpx_body"] = raw_resp.text[:300]
            except Exception as raw_e:
                debug_info["raw_httpx_error"] = f"{type(raw_e).__name__}: {raw_e}"

            # SDK call
            client = anth.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=8,
                messages=[{"role": "user", "content": "Reply: OK"}],
            )
            api_test = f"ok: {resp.content[0].text.strip()}"
        except Exception as e:
            api_test = f"{type(e).__name__}: {e}"
            debug_info["traceback"] = tb.format_exc()[-500:]

    return {
        "status": "ok",
        "anthropic_key_set": has_key,
        "key_prefix": key_prefix,
        "api_test": api_test,
        "debug": debug_info,
    }


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    min_gap_pct: float = Query(2.0, ge=0, le=50, description="Min gap size %"),
):
    """Upload a TradingView CSV and get full technical analysis."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "File is empty")

    try:
        parsed = _parse_upload(contents, file.filename)
    except ValueError as e:
        raise HTTPException(422, f"CSV parse error: {e}")
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {e}")

    return _run_full_analysis(parsed, min_gap_pct)


@app.post("/analyze/gaps")
async def analyze_gaps(
    file: UploadFile = File(...),
    min_gap_pct: float = Query(2.0, ge=0, le=50),
):
    """Upload CSV, return gap analysis only."""
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "File is empty")

    try:
        parsed = _parse_upload(contents, file.filename or "upload.csv")
    except ValueError as e:
        raise HTTPException(422, f"CSV parse error: {e}")

    gaps = detect_gaps(parsed.df, min_gap_pct=min_gap_pct)
    return {
        "metadata": _metadata(parsed),
        "gaps": summarize_gaps(gaps),
    }


@app.post("/analyze/levels")
async def analyze_levels(
    file: UploadFile = File(...),
):
    """Upload CSV, return support/resistance levels only."""
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "File is empty")

    try:
        parsed = _parse_upload(contents, file.filename or "upload.csv")
    except ValueError as e:
        raise HTTPException(422, f"CSV parse error: {e}")

    current_price = float(parsed.df["close"].iloc[-1])
    levels = calculate_levels(parsed.df, current_price=current_price)
    return {
        "metadata": _metadata(parsed),
        "support_resistance": summarize_levels(levels, current_price),
    }


@app.post("/analyze/zones")
async def analyze_zones(
    file: UploadFile = File(...),
):
    """Upload CSV, return supply/demand zones only."""
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "File is empty")

    try:
        parsed = _parse_upload(contents, file.filename or "upload.csv")
    except ValueError as e:
        raise HTTPException(422, f"CSV parse error: {e}")

    current_price = float(parsed.df["close"].iloc[-1])
    zones = identify_zones(parsed.df)
    return _sanitize({
        "metadata": _metadata(parsed),
        "supply_demand": summarize_zones(zones, current_price),
    })


@app.get("/tiers")
async def tiers():
    """List available analysis tiers with descriptions and cost limits."""
    return {"tiers": list_tiers()}


@app.post("/analyze/full")
async def analyze_full(
    file: UploadFile = File(...),
    symbol: Optional[str] = Query(None, description="Stock ticker symbol (e.g., WHR). Auto-detected from filename if omitted."),
    tier: str = Query("standard", description="Analysis tier: lite, standard, premium"),
    format: str = Query("json", description="Output format: json, markdown, html"),
    min_gap_pct: float = Query(2.0, ge=0, le=50, description="Min gap size %"),
):
    """Upload a TradingView CSV and run full AI-powered analysis.

    Runs the complete pipeline: technical analysis + news + SEC filings + Opus synthesis.
    The tier parameter controls analysis depth and cost.
    The format parameter controls the response format (json, markdown, html).
    Symbol is auto-detected from filename if not provided.
    """
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "File is empty")

    try:
        parsed = _parse_upload(contents, file.filename)
    except ValueError as e:
        raise HTTPException(422, f"CSV parse error: {e}")

    # Auto-detect symbol from parsed CSV if not provided
    effective_symbol = symbol or parsed.symbol

    try:
        orchestrator = TradingAnalysisOrchestrator(tier=tier)
        result = orchestrator.analyze_from_parsed(
            symbol=effective_symbol,
            parsed=parsed,
            min_gap_pct=min_gap_pct,
        )

        fmt = format.lower()
        if fmt == "json":
            return _sanitize(result)
        elif fmt == "markdown":
            report = orchestrator.generate_report(result, format="markdown")
            return PlainTextResponse(content=report, media_type="text/markdown")
        elif fmt == "html":
            report = orchestrator.generate_report(result, format="html")
            return HTMLResponse(content=report)
        else:
            raise HTTPException(400, f"Unknown format '{format}'. Choose: json, markdown, html")

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Analysis error: {e}")


@app.get("/analyze/sample/{filename}")
async def analyze_sample(
    filename: str,
    min_gap_pct: float = Query(2.0, ge=0, le=50),
):
    """Analyze a bundled sample CSV file (e.g., NYSE_WHR__1M.csv)."""
    # Prevent path traversal
    safe_name = Path(filename).name
    sample_path = SAMPLES_DIR / safe_name

    if not sample_path.exists():
        available = [f.name for f in SAMPLES_DIR.glob("*.csv")]
        raise HTTPException(
            404,
            f"Sample '{safe_name}' not found. Available: {available}",
        )

    parsed = load_csv(str(sample_path))
    return _run_full_analysis(parsed, min_gap_pct)
