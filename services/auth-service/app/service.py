import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import User
from .schemas import LoginRequest
from .security import create_access_token, pwd_context


def _load_seed_users() -> list[dict]:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data.get("auth", {}).get("users", [])


def seed_users(db: Session) -> None:
    users = _load_seed_users()
    if not users:
        return

    for seed_user in users:
        existing = db.scalar(select(User).where(User.email == seed_user["email"]))
        if not existing:
            existing = User(
                id=seed_user["id"],
                email=seed_user["email"],
                full_name=seed_user["full_name"],
                role=seed_user["role"],
                password_hash=pwd_context.hash(seed_user["password"]),
            )
            db.add(existing)
        else:
            existing.full_name = seed_user["full_name"]
            existing.role = seed_user["role"]
            existing.password_hash = pwd_context.hash(seed_user["password"])

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
