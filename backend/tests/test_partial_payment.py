import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.modules.billing.service import BillingService
from app.modules.billing.schemas import PaymentCreate
from app.modules.billing.models import PaymentMethod, PaymentStatus
from app.common.exceptions import ConflictError

@pytest.mark.asyncio
async def test_record_payment_prevents_overpayment():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    
    # Mock invoice returned by get_invoice
    mock_invoice = MagicMock()
    mock_invoice.total_amount = Decimal('100.00')
    mock_invoice.customer_phone = None
    
    # Mock existing payment of 60.00
    mock_payment = MagicMock()
    mock_payment.amount = Decimal('60.00')
    mock_payment.status = PaymentStatus.PAID
    mock_invoice.payments = [mock_payment]
    
    # Patch get_invoice
    import app.modules.billing.service
    original_get = app.modules.billing.service.BillingService.get_invoice
    app.modules.billing.service.BillingService.get_invoice = AsyncMock(return_value=mock_invoice)
    
    try:
        schema = PaymentCreate(
            invoice_id=uuid.uuid4(),
            method=PaymentMethod.CASH,
            amount=Decimal('50.00') # 60 + 50 = 110 > 100
        )
        
        with pytest.raises(ConflictError):
            await BillingService.record_payment(mock_db, uuid.uuid4(), schema)
            
        # Valid payment should not raise error
        schema_valid = PaymentCreate(
            invoice_id=uuid.uuid4(),
            method=PaymentMethod.CASH,
            amount=Decimal('40.00') # 60 + 40 = 100 <= 100
        )
        await BillingService.record_payment(mock_db, uuid.uuid4(), schema_valid)
        assert mock_invoice.payment_status == PaymentStatus.PAID
        
        # Partial payment
        schema_partial = PaymentCreate(
            invoice_id=uuid.uuid4(),
            method=PaymentMethod.CASH,
            amount=Decimal('10.00') # 60 + 10 = 70 < 100
        )
        await BillingService.record_payment(mock_db, uuid.uuid4(), schema_partial)
        assert mock_invoice.payment_status == PaymentStatus.PARTIALLY_PAID
        
    finally:
        app.modules.billing.service.BillingService.get_invoice = original_get
