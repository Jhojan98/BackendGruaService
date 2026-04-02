from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    unit_number: Mapped[str] = mapped_column(String(64), unique=True)
    truck_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="Available")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
