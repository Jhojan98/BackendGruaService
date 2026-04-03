import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import User
from .schemas import CreateUserRequest, LoginRequest, UpdateAnyUserRequest, UpdateUserMeRequest
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
                profile_image_url=seed_user.get("profile_image_url"),
                theme=seed_user.get("theme", "light"),
                language=seed_user.get("language", "es"),
                email_alerts=seed_user.get("email_alerts", True),
                sms_urgent_alerts=seed_user.get("sms_urgent_alerts", True),
                browser_notifications=seed_user.get("browser_notifications", True),
                employee_id=seed_user.get("employee_id"),
                office_location=seed_user.get("office_location"),
            )
            db.add(existing)
        else:
            existing.full_name = seed_user["full_name"]
            existing.role = seed_user["role"]
            existing.password_hash = pwd_context.hash(seed_user["password"])
            existing.profile_image_url = seed_user.get("profile_image_url")
            existing.theme = seed_user.get("theme", "light")
            existing.language = seed_user.get("language", "es")
            existing.email_alerts = seed_user.get("email_alerts", True)
            existing.sms_urgent_alerts = seed_user.get("sms_urgent_alerts", True)
            existing.browser_notifications = seed_user.get("browser_notifications", True)
            existing.employee_id = seed_user.get("employee_id")
            existing.office_location = seed_user.get("office_location")

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


def update_user_me(user_id: str, payload: UpdateUserMeRequest, db: Session) -> User:
    user = get_user_me(user_id, db)
    changes = payload.model_dump(exclude_none=True)

    new_email = changes.get("email")
    if new_email and new_email != user.email:
        existing = db.scalar(select(User).where(User.email == new_email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def create_user(payload: CreateUserRequest, db: Session) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        id=str(uuid4()),
        email=str(payload.email),
        full_name=payload.full_name,
        role=payload.role,
        password_hash=pwd_context.hash(payload.password),
        profile_image_url=payload.profile_image_url,
        theme=payload.theme,
        language=payload.language,
        email_alerts=payload.email_alerts,
        sms_urgent_alerts=payload.sms_urgent_alerts,
        browser_notifications=payload.browser_notifications,
        employee_id=payload.employee_id,
        office_location=payload.office_location,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.scalars(select(User).order_by(User.full_name, User.email)).all()


def update_any_user(user_id: str, payload: UpdateAnyUserRequest, db: Session) -> User:
    user = get_user_me(user_id, db)
    changes = payload.model_dump(exclude_none=True)

    new_email = changes.get("email")
    if new_email and new_email != user.email:
        existing = db.scalar(select(User).where(User.email == new_email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    new_password = changes.pop("password", None)
    if new_password is not None:
        user.password_hash = pwd_context.hash(new_password)

    for field, value in changes.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user
