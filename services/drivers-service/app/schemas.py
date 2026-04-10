import re
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

DriverStatus = Literal["Available", "On Trip", "Off Duty"]
DriverShift = Literal["Morning", "Evening", "Night", "Rotating"]


class DriverCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=128)
    unit: str = Field(min_length=1, max_length=64)
    status: DriverStatus = "Available"
    shift: DriverShift = "Morning"
    phone: str = Field(min_length=3, max_length=64)
    score: float = Field(default=4.5, ge=0, le=5)
    trips: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=1024, validation_alias=AliasChoices("image_url", "image"))

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized


class DriverUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=128)
    unit: str | None = Field(default=None, min_length=1, max_length=64)
    status: DriverStatus | None = None
    shift: DriverShift | None = None
    phone: str | None = Field(default=None, min_length=3, max_length=64)
    score: float | None = Field(default=None, ge=0, le=5)
    trips: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=1024, validation_alias=AliasChoices("image_url", "image"))

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized


class DriverResponse(BaseModel):
    id: str
    name: str
    role: str
    unit: str
    status: DriverStatus
    shift: DriverShift
    phone: str
    score: float
    trips: int
    image: str | None = None
    created_at: datetime
    updated_at: datetime
