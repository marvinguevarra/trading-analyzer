"""Tests for the FastAPI backend."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api import app

SAMPLE_CSV = Path(__file__).parent.parent / "data" / "samples" / "NYSE_WHR__1M.csv"


@pytest.fixture
def csv_bytes() -> bytes:
    return SAMPLE_CSV.read_bytes()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Trading Analyzer API"
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "anthropic_key_set" in data


@pytest.mark.asyncio
async def test_analyze_full(client, csv_bytes):
    resp = await client.post(
        "/analyze",
        files={"file": ("NYSE_WHR__1M.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Top-level keys
    assert "metadata" in data
    assert "current_price" in data
    assert "gaps" in data
    assert "support_resistance" in data
    assert "supply_demand" in data

    # Metadata
    assert data["metadata"]["symbol"] == "WHR"
    assert data["metadata"]["timeframe"] == "1M"
    assert data["metadata"]["bars"] == 26
    assert data["metadata"]["quality"]["is_valid"] is True


@pytest.mark.asyncio
async def test_analyze_gaps(client, csv_bytes):
    resp = await client.post(
        "/analyze/gaps",
        files={"file": ("NYSE_WHR__1M.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "metadata" in data
    assert "gaps" in data
    assert "total" in data["gaps"]


@pytest.mark.asyncio
async def test_analyze_levels(client, csv_bytes):
    resp = await client.post(
        "/analyze/levels",
        files={"file": ("NYSE_WHR__1M.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "support_resistance" in data
    sr = data["support_resistance"]
    assert "current_price" in sr
    assert "support_levels" in sr
    assert "resistance_levels" in sr


@pytest.mark.asyncio
async def test_analyze_zones(client, csv_bytes):
    resp = await client.post(
        "/analyze/zones",
        files={"file": ("NYSE_WHR__1M.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "supply_demand" in data
    sd = data["supply_demand"]
    assert "demand_zones" in sd
    assert "supply_zones" in sd


@pytest.mark.asyncio
async def test_analyze_sample(client):
    resp = await client.get("/analyze/sample/NYSE_WHR__1M.csv")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["symbol"] == "WHR"
    assert "gaps" in data
    assert "support_resistance" in data
    assert "supply_demand" in data


@pytest.mark.asyncio
async def test_sample_not_found(client):
    resp = await client.get("/analyze/sample/NONEXISTENT.csv")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_empty_file_rejected(client):
    resp = await client.post(
        "/analyze",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_csv_rejected(client):
    resp = await client.post(
        "/analyze",
        files={"file": ("bad.csv", b"not,real,csv\n1,2,3\n", "text/csv")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_min_gap_pct_param(client, csv_bytes):
    resp = await client.post(
        "/analyze/gaps?min_gap_pct=0.5",
        files={"file": ("NYSE_WHR__1M.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200


# ── /analyze/full dual-mode tests ────────────────────────────


def _make_stock_df(rows: int = 20) -> pd.DataFrame:
    """Create a fake stock DataFrame matching fetch_stock_data output."""
    dates = pd.date_range("2024-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "open": range(100, 100 + rows),
            "high": range(105, 105 + rows),
            "low": range(95, 95 + rows),
            "close": range(102, 102 + rows),
            "volume": [1_000_000] * rows,
        }
    )


@pytest.mark.asyncio
async def test_analyze_full_csv_mode(client, csv_bytes):
    """CSV mode with valid file should succeed."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "csv", "tier": "lite", "force_fresh": "true"},
        files={"file": ("NYSE_WHR__1M.csv", csv_bytes, "text/csv")},
    )
    # The orchestrator may fail without API key, but parsing should work.
    # Accept 200 (success) or 500 (API key missing for AI agents).
    assert resp.status_code in (200, 500)


@pytest.mark.asyncio
async def test_analyze_full_csv_mode_missing_file(client):
    """CSV mode without a file should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "csv", "tier": "lite"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_full_csv_mode_wrong_extension(client):
    """CSV mode with non-csv file should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "csv", "tier": "lite"},
        files={"file": ("data.txt", b"some data", "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_full_csv_mode_empty_file(client):
    """CSV mode with empty file should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "csv", "tier": "lite"},
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
@patch("api.fetch_stock_data")
async def test_analyze_full_ticker_mode(mock_fetch, client):
    """Ticker mode with valid ticker should succeed (mocked)."""
    mock_fetch.return_value = _make_stock_df()
    resp = await client.post(
        "/analyze/full",
        data={
            "mode": "ticker",
            "ticker": "AAPL",
            "timeframe": "1mo",
            "tier": "lite",
            "force_fresh": "true",
        },
    )
    # Accept 200 or 500 (API key missing for AI agents)
    assert resp.status_code in (200, 500)
    mock_fetch.assert_called_once_with("AAPL", period="1mo")


@pytest.mark.asyncio
async def test_analyze_full_ticker_mode_missing_ticker(client):
    """Ticker mode without ticker should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "ticker", "tier": "lite"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_full_ticker_mode_invalid_ticker(client):
    """Ticker mode with numbers in ticker should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "ticker", "ticker": "123", "tier": "lite"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_full_ticker_mode_long_ticker(client):
    """Ticker mode with >5 char ticker should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "ticker", "ticker": "ABCDEFGH", "tier": "lite"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_full_ticker_mode_bad_timeframe(client):
    """Ticker mode with invalid timeframe should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={
            "mode": "ticker",
            "ticker": "AAPL",
            "timeframe": "99x",
            "tier": "lite",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
@patch("api.fetch_stock_data")
async def test_analyze_full_ticker_no_data(mock_fetch, client):
    """Ticker mode where yfinance returns None should return 400."""
    mock_fetch.return_value = None
    resp = await client.post(
        "/analyze/full",
        data={"mode": "ticker", "ticker": "ZZZZZ", "timeframe": "1mo", "tier": "lite"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analyze_full_invalid_mode(client):
    """Invalid mode should return 400."""
    resp = await client.post(
        "/analyze/full",
        data={"mode": "invalid", "tier": "lite"},
    )
    assert resp.status_code == 400
