from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    membership: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(64))

    history: Mapped[list["ClientHistory"]] = relationship(back_populates="client")


class ClientHistory(Base):
    __tablename__ = "client_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    service_date: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(255))
    revenue: Mapped[float] = mapped_column(Float, default=0.0)

    client: Mapped[Client] = relationship(back_populates="history")
