import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.orders.service import OrderService
from app.modules.orders.schemas import OrderCreate, OrderItemCreate
from app.modules.orders.models import OrderType
from app.modules.menu.models import MenuItem

@pytest.mark.asyncio
async def test_create_order_ignores_client_price():
    db = AsyncMock()
    restaurant_id = uuid.uuid4()
    
    mock_menu_item = MagicMock(spec=MenuItem)
    mock_menu_item.id = uuid.uuid4()
    mock_menu_item.base_price = Decimal("25.00")
    mock_menu_item.name = "Real Steak"
    
    # Setup DB mock to return our real menu item
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_menu_item
    
    # First call is MenuItem lookup, then (since no branch_id/variant) we move on
    db.execute.return_value = mock_result
    
    # Client tries to send a fake price of 1.00
    schema = OrderCreate(
        order_type=OrderType.DINE_IN,
        items=[
            OrderItemCreate(
                menu_item_id=mock_menu_item.id,
                item_name="Fake Steak",
                quantity=2,
                unit_price=Decimal("1.00")
            )
        ]
    )
    
    # We mock OrderService._load_order to just return the saved order 
    # to avoid mocking all the relation loading
    with patch.object(OrderService, '_load_order', new_callable=AsyncMock) as mock_load_order, \
         patch.object(OrderService, '_generate_order_number', return_value="ORD-123"):
        
        mock_load_order.return_value = MagicMock()
        await OrderService.create_order(db, restaurant_id=restaurant_id, schema=schema)
    
    # Check that db.add was called with an Order item using the real price (25.00 * 2 = 50.00 subtotal)
    # Order is added first
    added_order = db.add.call_args_list[0][0][0]
    assert added_order.subtotal == Decimal("50.00")
    
    # OrderItem is added second
    added_order_item = db.add.call_args_list[1][0][0]
    assert added_order_item.unit_price == Decimal("25.00")
    assert added_order_item.item_name == "Real Steak"
