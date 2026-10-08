from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class JobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=20, max_length=50000)
    source_kind: Literal["pasted", "daily_feed_manual"] = "pasted"
    source_url: HttpUrl | None = None

    @field_validator("source_url")
    @classmethod
    def limit_url(cls, value):
        if value and len(str(value)) > 2048:
            raise ValueError("Source URL cannot exceed 2048 characters")
        return value


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    company: str
    description: str
    source_kind: str
    source_url: str | None
    created_at: datetime
