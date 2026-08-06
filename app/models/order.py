import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    ForeignKey,
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import OrderStatus
from app.models.kot import KOT


class Order(Base):
    __tablename__ = "orders"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    order_number = Column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )

    cart_id = Column(
        UUID(as_uuid=True),
        ForeignKey("carts.id"),
        nullable=False,
    )

    table_number = Column(
        String(20),
        nullable=True,
    )

    order_type = Column(
        String(20),
        nullable=False,
    )

    status = Column(
        SqlEnum(OrderStatus, name="orderstatus"),
        nullable=False,
        default=OrderStatus.PENDING,
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

    # ===========================
    # Relationships
    # ===========================

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    kot = relationship(
        "KOT",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )