from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class TariffBillingSettings(Base):
    __tablename__ = "tariff_billing_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    heavy_duty_tow: Mapped[float] = mapped_column(Float, default=150.0)
    medium_duty_tow: Mapped[float] = mapped_column(Float, default=95.0)
    jumpstart: Mapped[float] = mapped_column(Float, default=45.0)
    roadside_assist: Mapped[float] = mapped_column(Float, default=65.0)
    cost_per_mile: Mapped[float] = mapped_column(Float, default=4.5)
    free_distance_threshold: Mapped[float] = mapped_column(Float, default=5.0)
    after_hours_surcharge: Mapped[float] = mapped_column(Float, default=35.0)
    fuel_surcharge_percent: Mapped[float] = mapped_column(Float, default=8.5)
    severe_weather_fee: Mapped[float] = mapped_column(Float, default=50.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
