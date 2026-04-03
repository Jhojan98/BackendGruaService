from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="active")
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_type: Mapped[str] = mapped_column(String(32), default="corporate")
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_service_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    history: Mapped[list["ClientHistory"]] = relationship(back_populates="client")
    vehicles: Mapped[list["ClientVehicle"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class ClientHistory(Base):
    __tablename__ = "client_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    service_date: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(255))
    revenue: Mapped[float] = mapped_column(Float, default=0.0)

    client: Mapped[Client] = relationship(back_populates="history")


class ClientVehicle(Base):
    __tablename__ = "client_vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    make: Mapped[str] = mapped_column(String(128))
    model: Mapped[str] = mapped_column(String(128))
    license_plate: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    client: Mapped[Client] = relationship(back_populates="vehicles")
