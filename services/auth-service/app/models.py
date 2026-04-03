from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="dispatcher")
    password_hash: Mapped[str] = mapped_column(String(255))
    profile_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    theme: Mapped[str] = mapped_column(String(16), default="light")
    language: Mapped[str] = mapped_column(String(8), default="es")
    email_alerts: Mapped[bool] = mapped_column(default=True)
    sms_urgent_alerts: Mapped[bool] = mapped_column(default=True)
    browser_notifications: Mapped[bool] = mapped_column(default=True)
    employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    office_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
