from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User
from .schemas import LoginRequest
from .security import create_access_token, pwd_context


def seed_users(db: Session) -> None:
    admin = db.scalar(select(User).where(User.email == "admin@terra.local"))
    if not admin:
        admin = User(
            id="u-admin-1",
            email="admin@terra.local",
            full_name="Terra Admin",
            role="admin",
            password_hash=pwd_context.hash("admin123"),
        )
        db.add(admin)
    else:
        admin.full_name = "Terra Admin"
        admin.role = "admin"
        admin.password_hash = pwd_context.hash("admin123")

    dispatcher = db.scalar(select(User).where(User.email == "dispatcher@terra.local"))
    if not dispatcher:
        dispatcher = User(
            id="u-dispatch-1",
            email="dispatcher@terra.local",
            full_name="Dispatch Operator",
            role="dispatcher",
            password_hash=pwd_context.hash("dispatch123"),
        )
        db.add(dispatcher)
    else:
        dispatcher.full_name = "Dispatch Operator"
        dispatcher.role = "dispatcher"
        dispatcher.password_hash = pwd_context.hash("dispatch123")

    db.commit()


def login_user(payload: LoginRequest, db: Session) -> str:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_access_token(user.id, user.role)


def get_user_me(user_id: str, db: Session) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
