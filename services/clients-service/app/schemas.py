from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ClientStatus = Literal["active", "inactive", "suspended"]
ClientType = Literal["corporate", "individual"]


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=64)
    status: ClientStatus
    contact_person: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=5, max_length=255)
    client_type: ClientType
    logo_url: str | None = Field(default=None, max_length=1024)
    last_service_date: str | None = Field(default=None, max_length=16)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError("Invalid email format")
        return normalized

    @field_validator("last_service_date")
    @classmethod
    def validate_last_service_date(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        try:
            date.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("last_service_date must be YYYY-MM-DD") from exc
        return normalized


class ClientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=3, max_length=64)
    status: ClientStatus | None = None
    contact_person: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    client_type: ClientType | None = None
    logo_url: str | None = Field(default=None, max_length=1024)
    last_service_date: str | None = Field(default=None, max_length=16)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError("Invalid email format")
        return normalized

    @field_validator("last_service_date")
    @classmethod
    def validate_last_service_date(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        try:
            date.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("last_service_date must be YYYY-MM-DD") from exc
        return normalized


class ClientResponse(BaseModel):
    id: str
    name: str
    phone: str
    status: ClientStatus
    contact_person: str | None = None
    email: str | None = None
    client_type: ClientType
    logo_url: str | None = None
    last_service_date: str | None = None
    created_at: datetime
    updated_at: datetime


class ClientVehicleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    license_plate: str = Field(min_length=1, max_length=32)
    is_active: bool = True


class ClientVehicleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    make: str | None = Field(default=None, min_length=1, max_length=128)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    license_plate: str | None = Field(default=None, min_length=1, max_length=32)
    is_active: bool | None = None


class ClientVehicleResponse(BaseModel):
    id: str
    client_id: str
    make: str
    model: str
    license_plate: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClientHistoryResponse(BaseModel):
    id: str
    serviceDate: str
    description: str
    revenue: float
