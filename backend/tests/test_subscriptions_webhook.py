import pytest
import hmac
import hashlib
import json
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings

@pytest.fixture
def mock_webhook_payload():
    return {"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_123"}}}}

@pytest.fixture
def raw_body(mock_webhook_payload):
    return json.dumps(mock_webhook_payload).encode('utf-8')

@pytest.fixture
def valid_signature(raw_body):
    return hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()

@pytest.mark.asyncio
async def test_webhook_missing_signature(raw_body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Don't pass X-Razorpay-Signature header
        response = await client.post(
            "/api/v1/subscriptions/webhook/razorpay", 
            content=raw_body,
            headers={"Content-Type": "application/json"}
        )
    
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MISSING_SIGNATURE"

@pytest.mark.asyncio
async def test_webhook_invalid_signature(raw_body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/subscriptions/webhook/razorpay", 
            content=raw_body,
            headers={"X-Razorpay-Signature": "invalid_signature_hash", "Content-Type": "application/json"}
        )
    
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_SIGNATURE"

@pytest.mark.asyncio
async def test_webhook_valid_signature(raw_body, valid_signature):
    # Mock SubscriptionService.handle_razorpay_webhook so it doesn't need DB access
    with patch('app.modules.subscriptions.service.SubscriptionService.handle_razorpay_webhook') as mock_handle:
        from unittest.mock import AsyncMock
        mock_handle.side_effect = AsyncMock(return_value={"status": "success"})
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/subscriptions/webhook/razorpay", 
                content=raw_body,
                headers={"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
            )
        
        assert response.status_code == 200
        mock_handle.assert_called_once()
