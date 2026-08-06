import pytest
from httpx import AsyncClient, ASGITransport
import uuid

from app.main import app
from app.core.db import get_db
from unittest.mock import patch

async def override_get_db():
    yield None

app.dependency_overrides[get_db] = override_get_db

@pytest.mark.asyncio
async def test_auth_rate_limiting():
    # settings.RATE_LIMIT_AUTH is "5/minute"
    # We will send 6 requests, the 6th should be rate limited (429)
    # We pass a unique IP in headers to avoid side effects from other tests, 
    # but ASGITransport sets client IP to 127.0.0.1 by default. 
    # We'll rely on the default behavior since this test runs sequentially.
    
    login_payload = {
        "email": f"test_{uuid.uuid4()}@example.com",
        "password": "wrongpassword123"
    }

    from unittest.mock import patch, AsyncMock
    with patch('app.modules.auth.service.AuthService.login_user') as mock_login:
        from app.modules.auth.schemas import Token, UserResponse
        from datetime import datetime
        mock_user = UserResponse(id=uuid.uuid4(), email="test@test.com", full_name="Test", created_at=datetime.utcnow(), is_active=True, is_verified=True, roles=[])
        mock_login.side_effect = AsyncMock(return_value=Token(access_token="acc", refresh_token="ref", token_type="bearer", user=mock_user))
        
        test_ip = f"192.168.{uuid.uuid4().int % 200 + 1}.{uuid.uuid4().int % 200 + 1}"
        async with AsyncClient(transport=ASGITransport(app=app, client=(test_ip, 1234)), base_url="http://testserver") as client:
            # First 5 requests should pass the rate limiter and hit the actual endpoint (which returns 401 or 404 for wrong credentials)
            for _ in range(5):
                response = await client.post("/api/v1/auth/login", json=login_payload)
                # Make sure it's NOT a 429
                assert response.status_code != 429

            # The 6th request should hit the rate limiter
            response = await client.post("/api/v1/auth/login", json=login_payload)
            assert response.status_code == 429
            data = response.json()
            assert "Rate limit exceeded" in str(data)
