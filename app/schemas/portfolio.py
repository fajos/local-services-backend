from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class PortfolioItemCreate(BaseModel):
    title: str | None = None
    image_url: str

class PortfolioItemOut(BaseModel):
    id: UUID
    provider_id: UUID
    title: str | None = None
    image_url: str
    created_at: datetime

    class Config:
        from_attributes = True
