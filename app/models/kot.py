import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import KOTStatus
from sqlalchemy import Enum


class KOT(Base):
    __tablename__ = "kots"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    kot_number = Column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    status = Column(
    Enum(
        KOTStatus,
        values_callable=lambda obj: [e.value for e in obj],
        name="kotstatus",
    ),
    nullable=False,
    default=KOTStatus.PENDING,
)
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    order = relationship(
        "Order",
        back_populates="kot",
    )