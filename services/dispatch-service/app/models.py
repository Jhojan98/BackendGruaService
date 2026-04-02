from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


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
