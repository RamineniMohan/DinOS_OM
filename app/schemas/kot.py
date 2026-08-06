from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import KOTStatus


class CreateKOTRequest(BaseModel):
    order_id: UUID


class UpdateKOTStatusRequest(BaseModel):
    status: KOTStatus


class KOTResponse(BaseModel):

    id: UUID

    kot_number: str

    order_id: UUID

    status: KOTStatus

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )