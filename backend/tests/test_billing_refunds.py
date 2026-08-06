import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.modules.billing.service import BillingService
from app.modules.billing.models import Payment, PaymentStatus, Refund
from app.modules.billing.schemas import RefundCreate
from app.common.exceptions import ConflictError, NotFoundError

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_payment():
    payment = MagicMock(spec=Payment)
    payment.id = uuid.uuid4()
    payment.amount = Decimal("100.00")
    payment.status = PaymentStatus.PAID
    
    invoice = MagicMock()
    invoice.restaurant_id = uuid.uuid4()
    invoice.customer_phone = None # Skip CRM stuff for basic refund test
    payment.invoice = invoice
    
    return payment

@pytest.mark.asyncio
async def test_process_refund_full(mock_db, mock_payment):
    # Setup mocks
    mock_payment_result = MagicMock()
    mock_payment_result.scalar_one_or_none.return_value = mock_payment
    
    mock_refunds_result = MagicMock()
    mock_refunds_result.scalars().all.return_value = [] # No existing refunds
    
    mock_db.execute.side_effect = [mock_payment_result, mock_refunds_result]
    
    schema = RefundCreate(payment_id=mock_payment.id, amount=Decimal("100.00"), reason="Customer requested")
    
    refund = await BillingService.process_refund(mock_db, mock_payment.invoice.restaurant_id, schema)
    
    assert refund.amount == Decimal("100.00")
    assert refund.status == 'completed'
    assert mock_payment.status == PaymentStatus.REFUNDED
    assert mock_db.add.called
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_process_refund_partial(mock_db, mock_payment):
    # Setup mocks
    mock_payment_result = MagicMock()
    mock_payment_result.scalar_one_or_none.return_value = mock_payment
    
    mock_refunds_result = MagicMock()
    mock_refunds_result.scalars().all.return_value = [] # No existing refunds
    
    mock_db.execute.side_effect = [mock_payment_result, mock_refunds_result]
    
    schema = RefundCreate(payment_id=mock_payment.id, amount=Decimal("40.00"), reason="Partial refund")
    
    refund = await BillingService.process_refund(mock_db, mock_payment.invoice.restaurant_id, schema)
    
    assert refund.amount == Decimal("40.00")
    assert mock_payment.status == PaymentStatus.PAID # Status only changes on full refund
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_process_refund_exceeds_amount(mock_db, mock_payment):
    # Setup mocks
    mock_payment_result = MagicMock()
    mock_payment_result.scalar_one_or_none.return_value = mock_payment
    
    # Existing refund of 60
    existing_refund = MagicMock(spec=Refund)
    existing_refund.amount = Decimal("60.00")
    existing_refund.status = "completed"
    
    mock_refunds_result = MagicMock()
    mock_refunds_result.scalars().all.return_value = [existing_refund]
    
    mock_db.execute.side_effect = [mock_payment_result, mock_refunds_result]
    
    # Try to refund another 50 (total 110 > 100)
    schema = RefundCreate(payment_id=mock_payment.id, amount=Decimal("50.00"))
    
    with pytest.raises(ConflictError) as excinfo:
        await BillingService.process_refund(mock_db, mock_payment.invoice.restaurant_id, schema)
    
    assert excinfo.value.status_code == 409
    assert excinfo.value.message == "Refund amount exceeds paid amount"

@pytest.mark.asyncio
async def test_process_refund_unpaid_payment(mock_db, mock_payment):
    mock_payment.status = PaymentStatus.PENDING
    
    mock_payment_result = MagicMock()
    mock_payment_result.scalar_one_or_none.return_value = mock_payment
    
    mock_db.execute.return_value = mock_payment_result
    
    schema = RefundCreate(payment_id=mock_payment.id, amount=Decimal("100.00"))
    
    with pytest.raises(ConflictError) as excinfo:
        await BillingService.process_refund(mock_db, mock_payment.invoice.restaurant_id, schema)
    
    assert excinfo.value.message == "Cannot refund an unpaid or failed payment"
