from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TariffBillingResponse(BaseModel):
    id: int
    heavy_duty_tow: float
    medium_duty_tow: float
    jumpstart: float
    roadside_assist: float
    cost_per_mile: float
    free_distance_threshold: float
    after_hours_surcharge: float
    fuel_surcharge_percent: float
    severe_weather_fee: float
    created_at: datetime
    updated_at: datetime


class TariffBillingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heavy_duty_tow: float | None = Field(default=None, ge=0)
    medium_duty_tow: float | None = Field(default=None, ge=0)
    jumpstart: float | None = Field(default=None, ge=0)
    roadside_assist: float | None = Field(default=None, ge=0)
    cost_per_mile: float | None = Field(default=None, ge=0)
    free_distance_threshold: float | None = Field(default=None, ge=0)
    after_hours_surcharge: float | None = Field(default=None, ge=0)
    fuel_surcharge_percent: float | None = Field(default=None, ge=0)
    severe_weather_fee: float | None = Field(default=None, ge=0)
