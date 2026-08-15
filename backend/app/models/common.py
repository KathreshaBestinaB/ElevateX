"""Common base models shared across domain models."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class AppBaseModel(BaseModel):
    """Base for all domain models — configures serialization."""
    model_config = {"populate_by_name": True}


class TimestampedModel(AppBaseModel):
    """Adds created_at / updated_at to domain models."""
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
