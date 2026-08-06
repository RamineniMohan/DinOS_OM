import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.modules.crm.service import CRMService, POINTS_PER_RUPEE_RATIO, POINT_VALUE
from app.modules.crm.models import Customer, LoyaltyTransaction
from app.common.exceptions import NotFoundError, AppException

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_customer():
    customer = MagicMock(spec=Customer)
    customer.id = uuid.uuid4()
    customer.restaurant_id = uuid.uuid4()
    customer.loyalty_points = 100
    customer.visits_count = 5
    return customer

@pytest.mark.asyncio
async def test_accrue_points_success(mock_db, mock_customer):
    # First execute returns customer; second returns None (no existing accrual for this order)
    mock_customer_result = MagicMock()
    mock_customer_result.scalar_one_or_none.return_value = mock_customer
    mock_no_txn_result = MagicMock()
    mock_no_txn_result.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [mock_customer_result, mock_no_txn_result]

    amount_paid = Decimal('150.00')
    order_id = uuid.uuid4()
    # Expected points = 150 * 0.1 = 15
    expected_points = 15

    txn = await CRMService.accrue_points(
        mock_db,
        customer_id=mock_customer.id,
        restaurant_id=mock_customer.restaurant_id,
        amount_paid=amount_paid,
        order_id=order_id,
    )

    assert mock_customer.loyalty_points == 115
    assert mock_customer.visits_count == 6
    assert txn.points_change == expected_points
    assert txn.transaction_type == 'accrual'
    mock_db.add.assert_called_with(txn)

@pytest.mark.asyncio
async def test_accrue_points_zero_amount(mock_db, mock_customer):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_customer
    mock_db.execute.return_value = mock_result

    amount_paid = Decimal('5.00')
    # 5 * 0.1 = 0.5 -> int(0.5) = 0
    txn = await CRMService.accrue_points(
        mock_db,
        customer_id=mock_customer.id,
        restaurant_id=mock_customer.restaurant_id,
        amount_paid=amount_paid
    )

    assert txn is None
    assert mock_customer.loyalty_points == 100

@pytest.mark.asyncio
async def test_redeem_points_success(mock_db, mock_customer):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_customer
    mock_db.execute.return_value = mock_result

    points_to_redeem = 50
    # Expected discount = 50 * 0.50 = 25.00
    expected_discount = Decimal('25.00')

    discount = await CRMService.redeem_points(
        mock_db,
        customer_id=mock_customer.id,
        restaurant_id=mock_customer.restaurant_id,
        points_to_redeem=points_to_redeem
    )

    assert discount == expected_discount
    assert mock_customer.loyalty_points == 50
    
    added_txn = mock_db.add.call_args[0][0]
    assert added_txn.points_change == -50
    assert added_txn.transaction_type == 'redemption'

@pytest.mark.asyncio
async def test_redeem_points_insufficient(mock_db, mock_customer):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_customer
    mock_db.execute.return_value = mock_result

    points_to_redeem = 200 # More than 100

    with pytest.raises(AppException) as excinfo:
        await CRMService.redeem_points(
            mock_db,
            customer_id=mock_customer.id,
            restaurant_id=mock_customer.restaurant_id,
            points_to_redeem=points_to_redeem
        )
    
    assert excinfo.value.status_code == 400
    assert excinfo.value.code == 'INSUFFICIENT_POINTS'
    assert mock_customer.loyalty_points == 100 # Unchanged
