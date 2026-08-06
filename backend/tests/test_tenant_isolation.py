import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.modules.orders.service import OrderService
from app.modules.menu.service import MenuService
from app.modules.crm.service import CRMService
from app.modules.billing.service import BillingService
from app.modules.inventory.service import InventoryService
from app.modules.operations.service import OperationsService
from app.common.exceptions import NotFoundError

@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    # Simulate DB finding nothing (which is what happens when restaurant_id doesn't match)
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    return db

@pytest.mark.asyncio
async def test_order_cross_tenant_returns_404(mock_db):
    with pytest.raises(NotFoundError):
        await OrderService.get_order(mock_db, order_id=uuid.uuid4(), restaurant_id=uuid.uuid4())

@pytest.mark.asyncio
async def test_menu_cross_tenant_returns_404(mock_db):
    with pytest.raises(NotFoundError):
        await MenuService.delete_item(mock_db, item_id=uuid.uuid4(), restaurant_id=uuid.uuid4())

@pytest.mark.asyncio
async def test_crm_cross_tenant_returns_404(mock_db):
    with pytest.raises(NotFoundError):
        await CRMService.get_customer(mock_db, customer_id=uuid.uuid4(), restaurant_id=uuid.uuid4())

@pytest.mark.asyncio
async def test_billing_cross_tenant_returns_404(mock_db):
    with pytest.raises(NotFoundError):
        await BillingService.get_invoice(mock_db, invoice_id=uuid.uuid4(), restaurant_id=uuid.uuid4())

@pytest.mark.asyncio
async def test_inventory_cross_tenant_returns_404(mock_db):
    with pytest.raises(NotFoundError):
        await InventoryService.get_ingredient(mock_db, ingredient_id=uuid.uuid4(), restaurant_id=uuid.uuid4())

@pytest.mark.asyncio
async def test_operations_cross_tenant_returns_404(mock_db):
    # For operations, tables check
    from app.modules.operations.schemas import DiningTableUpdate
    with pytest.raises(NotFoundError):
        await OperationsService.update_table(mock_db, table_id=uuid.uuid4(), restaurant_id=uuid.uuid4(), schema=DiningTableUpdate())

@pytest.mark.asyncio
async def test_create_order_cross_tenant_item_returns_404(mock_db):
    from app.modules.orders.schemas import OrderCreate, OrderItemCreate
    from app.modules.orders.models import OrderType
    from decimal import Decimal

    schema = OrderCreate(
        order_type=OrderType.DINE_IN,
        items=[
            OrderItemCreate(
                menu_item_id=uuid.uuid4(),
                item_name="Steak",
                quantity=1,
                unit_price=Decimal("10.00")
            )
        ]
    )
    with pytest.raises(NotFoundError):
        await OrderService.create_order(mock_db, restaurant_id=uuid.uuid4(), schema=schema)

@pytest.mark.asyncio
async def test_deduct_inventory_cross_tenant_returns_no_deduction(mock_db):
    from unittest.mock import MagicMock
    # If the recipe is from another tenant, it won't be found
    mock_order = MagicMock()
    mock_order.restaurant_id = uuid.uuid4()
    mock_order.inventory_deducted = False
    
    order_item = MagicMock()
    order_item.menu_item_id = uuid.uuid4()
    order_item.quantity = 1
    mock_order.items = [order_item]

    # Setup DB mock to return None when searching for Recipe
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    await OrderService._deduct_inventory(mock_db, mock_order)
    
    # Assert that no StockLedger was added since recipe was not found
    assert not mock_db.add.called

@pytest.mark.asyncio
async def test_create_ingredient_cross_tenant_unit_returns_404(mock_db):
    from app.modules.inventory.schemas import IngredientCreate
    from decimal import Decimal
    schema = IngredientCreate(
        name="Salt",
        unit_id=uuid.uuid4(),
        current_stock=Decimal("10"),
        low_stock_threshold=Decimal("2"),
        cost_per_unit=Decimal("1")
    )
    with pytest.raises(NotFoundError):
        await InventoryService.create_ingredient(mock_db, restaurant_id=uuid.uuid4(), schema=schema)

@pytest.mark.asyncio
async def test_create_recipe_cross_tenant_menu_item_returns_404(mock_db):
    from app.modules.inventory.schemas import RecipeCreate
    from decimal import Decimal
    schema = RecipeCreate(
        menu_item_id=uuid.uuid4(),
        name="Salted Water",
        yield_quantity=Decimal("1"),
        ingredients=[]
    )
    with pytest.raises(NotFoundError):
        await InventoryService.create_recipe(mock_db, restaurant_id=uuid.uuid4(), schema=schema)

@pytest.mark.asyncio
async def test_create_recipe_cross_tenant_ingredient_returns_404():
    # specifically mock db to pass the menu item check and existing recipe check, but fail on ingredient
    from app.modules.inventory.schemas import RecipeCreate, RecipeIngredientCreate
    from unittest.mock import MagicMock, AsyncMock
    from decimal import Decimal
    db = AsyncMock()
    
    mock_menu_item = MagicMock()
    mock_menu_item_result = MagicMock()
    mock_menu_item_result.scalar_one_or_none.return_value = mock_menu_item
    
    mock_existing_recipe_result = MagicMock()
    mock_existing_recipe_result.scalar_one_or_none.return_value = None
    
    mock_ing_result = MagicMock()
    mock_ing_result.scalar_one_or_none.return_value = None
    
    db.execute.side_effect = [mock_menu_item_result, mock_existing_recipe_result, mock_ing_result]
    
    schema = RecipeCreate(
        menu_item_id=uuid.uuid4(),
        name="Salted Water",
        yield_quantity=Decimal("1"),
        ingredients=[
            RecipeIngredientCreate(
                ingredient_id=uuid.uuid4(),
                quantity=Decimal("1"),
                unit_id=uuid.uuid4()
            )
        ]
    )
    with pytest.raises(NotFoundError):
        await InventoryService.create_recipe(db, restaurant_id=uuid.uuid4(), schema=schema)

@pytest.mark.asyncio
async def test_create_table_cross_tenant_section_returns_404(mock_db):
    from app.modules.operations.schemas import DiningTableCreate
    schema = DiningTableCreate(
        table_number="10",
        section_id=uuid.uuid4(),
        capacity=4
    )
    with pytest.raises(NotFoundError):
        await OperationsService.create_table(mock_db, restaurant_id=uuid.uuid4(), schema=schema)
