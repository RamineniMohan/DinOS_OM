import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    DateTime,
    Numeric,
    String,
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import CartStatus


class Cart(Base):
    __tablename__ = "carts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    customer_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    table_number = Column(
        String(20),
        nullable=True,
    )

    order_type = Column(
        String(20),
        nullable=False,
        default="dine_in",
    )

    status = Column(
        SqlEnum(CartStatus, name="cartstatus"),
        nullable=False,
        default=CartStatus.ACTIVE,
    )

    subtotal = Column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    tax = Column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    discount = Column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    total = Column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    items = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )