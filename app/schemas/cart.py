from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field,ConfigDict
from uuid import UUID

#create cart

class CreateCartRequest(BaseModel):
    customer_id: Optional[UUID] = None
    table_number: Optional[str] = None
    order_type: str = "DINE_IN"  # dine_in, take_away, delivery


#ADD Item

class AddCartItemRequest(BaseModel):
    menu_item_id: UUID
    item_name: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    special_instructions: Optional[str] = None

#Update Quantity

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., gt=0)

#Cart Item Response
class CartItemResponse(BaseModel):
    id: UUID
    menu_item_id: UUID
    item_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    special_instructions: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

#cart Response
class CartResponse(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
    table_number: Optional[str] = None
    order_type: str
    status: str
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    items: List[CartItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

#Remove Item Request
class RemoveCartItemRequest(BaseModel):
    cart_item_id: UUID

#clear cart request
class ClearCartRequest(BaseModel):
    message : str = "Are you sure you want to clear the cart?"

# common response model
class MessageResponse(BaseModel):
    message: str