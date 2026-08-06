import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from app.modules.orders.service import OrderService
from app.modules.inventory.models import Ingredient, StockLedger

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_order():
    order = MagicMock()
    order.id = uuid.uuid4()
    order.restaurant_id = uuid.uuid4()
    order.inventory_deducted = False
    
    order_item = MagicMock()
    order_item.menu_item_id = uuid.uuid4()
    order_item.quantity = 2
    order.items = [order_item]
    
    return order

@pytest.fixture
def mock_recipe(mock_order):
    recipe = MagicMock()
    recipe_ingredient = MagicMock()
    recipe_ingredient.ingredient_id = uuid.uuid4()
    recipe_ingredient.quantity = Decimal("1.5") # 1.5 per item
    recipe.ingredients = [recipe_ingredient]
    return recipe

@pytest.fixture
def mock_ingredient(mock_recipe):
    ing = MagicMock(spec=Ingredient)
    ing.id = mock_recipe.ingredients[0].ingredient_id
    ing.name = "Tomato"
    ing.current_stock = Decimal("10.0")
    ing.low_stock_threshold = Decimal("2.0")
    return ing

@pytest.mark.asyncio
async def test_deduct_inventory_sufficient_stock(mock_db, mock_order, mock_recipe, mock_ingredient):
    # Setup mocks
    mock_recipe_result = MagicMock()
    mock_recipe_result.scalar_one_or_none.return_value = mock_recipe
    
    mock_ing_result = MagicMock()
    mock_ing_result.scalar_one_or_none.return_value = mock_ingredient
    
    # db.execute will be called twice: once for recipe, once for ingredient
    mock_db.execute.side_effect = [mock_recipe_result, mock_ing_result]
    
    await OrderService._deduct_inventory(mock_db, mock_order)
    
    # Order quantity 2 * Recipe quantity 1.5 = 3.0
    # Expected stock: 10 - 3 = 7
    assert mock_ingredient.current_stock == Decimal("7.0")
    assert mock_order.inventory_deducted is True
    assert mock_db.add.called
    
    # Check that a StockLedger entry was added
    added_obj = mock_db.add.call_args[0][0]
    assert isinstance(added_obj, StockLedger)
    assert added_obj.quantity_change == Decimal("-3.0")
    assert added_obj.quantity_before == Decimal("10.0")
    assert added_obj.quantity_after == Decimal("7.0")

@pytest.mark.asyncio
async def test_deduct_inventory_insufficient_stock_clamps_to_zero(mock_db, mock_order, mock_recipe, mock_ingredient):
    # Set stock lower than required (required is 3.0)
    mock_ingredient.current_stock = Decimal("2.0")
    
    mock_recipe_result = MagicMock()
    mock_recipe_result.scalar_one_or_none.return_value = mock_recipe
    mock_ing_result = MagicMock()
    mock_ing_result.scalar_one_or_none.return_value = mock_ingredient
    
    mock_db.execute.side_effect = [mock_recipe_result, mock_ing_result]
    
    await OrderService._deduct_inventory(mock_db, mock_order)
    
    # Since required was 3.0 but stock was 2.0, it should clamp to 0
    assert mock_ingredient.current_stock == Decimal("0.0")
    assert mock_order.inventory_deducted is True
    
    added_obj = mock_db.add.call_args[0][0]
    assert isinstance(added_obj, StockLedger)
    assert added_obj.quantity_change == Decimal("-2.0")
    assert added_obj.quantity_before == Decimal("2.0")
    assert added_obj.quantity_after == Decimal("0.0")

@pytest.mark.asyncio
async def test_deduct_inventory_already_deducted(mock_db, mock_order):
    mock_order.inventory_deducted = True
    
    await OrderService._deduct_inventory(mock_db, mock_order)
    
    # Should exit early, db.execute should not be called
    mock_db.execute.assert_not_called()
