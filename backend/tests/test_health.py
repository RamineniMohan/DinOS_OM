"""
Minimal health-check test — verifies the FastAPI app starts and /health returns 200.
Run with:  pytest backend/tests --asyncio-mode=auto
"""
import pytest
from httpx import AsyncClient, ASGITransport

# Import the ASGI app.  Avoids loading the real DB/Redis — just tests routing.
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
