import re
from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class TruckResponse(BaseModel):
    id: str
    unitNumber: str
    type: str
    status: str
    imageUrl: str | None = None
    assignedDriverId: str | None = None
    assignedDriverName: str | None = None
    assignedDriverStatus: str | None = None
    assignedDriverImage: str | None = None


class LocationResponse(BaseModel):
    truckId: str
    unitNumber: str
    lat: float
    lng: float
    status: str


class TruckStatusUpdate(BaseModel):
    status: str


class TruckDetailResponse(TruckResponse):
    lat: float
    lng: float


class TruckCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    unit_number: str = Field(alias="unitNumber", min_length=1, max_length=64)
    truck_type: str = Field(alias="type", min_length=1, max_length=64)
    status: Literal["Available", "On Trip", "Maintenance"] = "Available"
    lat: float = 0.0
    lng: float = 0.0
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024, validation_alias=AliasChoices("image_url", "image", "imageUrl"))


class TruckUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    unit_number: str | None = Field(default=None, alias="unitNumber", min_length=1, max_length=64)
    truck_type: str | None = Field(default=None, alias="type", min_length=1, max_length=64)
    status: Literal["Available", "On Trip", "Maintenance"] | None = None
    lat: float | None = None
    lng: float | None = None
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024, validation_alias=AliasChoices("image_url", "image", "imageUrl"))


class TruckDriverAssignRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    driver_id: str = Field(alias="driverId", min_length=1, max_length=36)


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
    assignedTruckId: str | None = None
    assignedTruckUnit: str | None = None
    assignedTruckType: str | None = None
    assignedTruckStatus: str | None = None
    created_at: datetime
    updated_at: datetime


class TripCreate(BaseModel):
    client_id: str
    client_name: str | None = None
    origin: str
    destination: str
    distance: str = "0 km"


class TripStatusUpdate(BaseModel):
    status: str


class TripAssignRequest(BaseModel):
    tow_truck: str


class TripResponse(BaseModel):
    id: str
    clientId: str
    clientName: str
    origin: str
    destination: str
    distance: str
    status: str
    towTruck: str
    date: str
    time: str
    driverId: str | None = None
    driverName: str | None = None
