from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    unit_number: Mapped[str] = mapped_column(String(64), unique=True)
    truck_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="Available")
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    # True 1:1 assignment at DB level: one truck can have at most one driver.
    driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"), unique=True, nullable=True)

    driver: Mapped["Driver | None"] = relationship("Driver", back_populates="truck", uselist=False)


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="Available")
    shift: Mapped[str] = mapped_column(String(32), default="Morning")
    phone: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float, default=4.5)
    trips: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    truck: Mapped[Truck | None] = relationship("Truck", back_populates="driver", uselist=False)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    client_name: Mapped[str] = mapped_column(String(255))
    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    distance: Mapped[str] = mapped_column(String(32), default="0 km")
    status: Mapped[str] = mapped_column(String(32), default="Pending")
    tow_truck: Mapped[str] = mapped_column(String(64), default="Unassigned")
    date: Mapped[str] = mapped_column(String(16))
    time: Mapped[str] = mapped_column(String(16))
    assigned_driver_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True)
    assigned_driver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
