"""Tests for the FastAPI backend."""

from pathlib import Path

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
    assert resp.json() == {"status": "ok"}


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
