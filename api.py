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

import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    return {"status": "ok"}


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
    symbol: str = Query(..., description="Stock ticker symbol (e.g., WHR)"),
    tier: str = Query("standard", description="Analysis tier: lite, standard, premium"),
    min_gap_pct: float = Query(2.0, ge=0, le=50, description="Min gap size %"),
):
    """Upload a TradingView CSV and run full AI-powered analysis.

    Runs the complete pipeline: technical analysis + news + SEC filings + Opus synthesis.
    The tier parameter controls analysis depth and cost.
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

    try:
        orchestrator = TradingAnalysisOrchestrator(tier=tier)
        result = orchestrator.analyze_from_parsed(
            symbol=symbol,
            parsed=parsed,
            min_gap_pct=min_gap_pct,
        )
        return _sanitize(result)
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
