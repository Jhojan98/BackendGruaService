from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import CreateUserRequest, LoginRequest, TokenResponse, UpdateAnyUserRequest, UpdateUserMeRequest, UserMeResponse, VerifyTokenRequest, VerifyTokenResponse
from .security import decode_token
from .service import create_user, get_user_me, list_users, login_user, seed_users, update_any_user, update_user_me

app = FastAPI(title="Auth Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_user_schema(db: Session) -> None:
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(1024)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS theme VARCHAR(16) DEFAULT 'light'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(8) DEFAULT 'es'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_alerts BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS sms_urgent_alerts BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS browser_notifications BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_id VARCHAR(64)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS office_location VARCHAR(255)",
        "UPDATE users SET theme = 'light' WHERE theme IS NULL",
        "UPDATE users SET language = 'es' WHERE language IS NULL",
        "UPDATE users SET email_alerts = TRUE WHERE email_alerts IS NULL",
        "UPDATE users SET sms_urgent_alerts = TRUE WHERE sms_urgent_alerts IS NULL",
        "UPDATE users SET browser_notifications = TRUE WHERE browser_notifications IS NULL",
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_user_schema(db)
        seed_users(db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth-service"}


@app.post("/internal/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    token = login_user(payload, db)
    return TokenResponse(access_token=token, token_type="bearer")


@app.post("/internal/auth/verify", response_model=VerifyTokenResponse)
def verify_token(payload: VerifyTokenRequest) -> VerifyTokenResponse:
    decoded = decode_token(payload.token)
    return VerifyTokenResponse(sub=decoded["sub"], role=decoded.get("role", "dispatcher"))


@app.get("/internal/users/me", response_model=UserMeResponse)
def me(user_id: str, db: Annotated[Session, Depends(get_db)]) -> UserMeResponse:
    user = get_user_me(user_id, db)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        profile_image_url=user.profile_image_url,
        theme=user.theme,
        language=user.language,
        email_alerts=user.email_alerts,
        sms_urgent_alerts=user.sms_urgent_alerts,
        browser_notifications=user.browser_notifications,
        employee_id=user.employee_id,
        office_location=user.office_location,
    )


@app.patch("/internal/users/me", response_model=UserMeResponse)
def update_me(
    user_id: str,
    payload: UpdateUserMeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> UserMeResponse:
    user = update_user_me(user_id, payload, db)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        profile_image_url=user.profile_image_url,
        theme=user.theme,
        language=user.language,
        email_alerts=user.email_alerts,
        sms_urgent_alerts=user.sms_urgent_alerts,
        browser_notifications=user.browser_notifications,
        employee_id=user.employee_id,
        office_location=user.office_location,
    )


@app.post("/internal/users", response_model=UserMeResponse, status_code=201)
def create_user_endpoint(payload: CreateUserRequest, db: Annotated[Session, Depends(get_db)]) -> UserMeResponse:
    user = create_user(payload, db)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        profile_image_url=user.profile_image_url,
        theme=user.theme,
        language=user.language,
        email_alerts=user.email_alerts,
        sms_urgent_alerts=user.sms_urgent_alerts,
        browser_notifications=user.browser_notifications,
        employee_id=user.employee_id,
        office_location=user.office_location,
    )


@app.get("/internal/users", response_model=list[UserMeResponse])
def list_users_endpoint(db: Annotated[Session, Depends(get_db)]) -> list[UserMeResponse]:
    users = list_users(db)
    return [
        UserMeResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            profile_image_url=user.profile_image_url,
            theme=user.theme,
            language=user.language,
            email_alerts=user.email_alerts,
            sms_urgent_alerts=user.sms_urgent_alerts,
            browser_notifications=user.browser_notifications,
            employee_id=user.employee_id,
            office_location=user.office_location,
        )
        for user in users
    ]


@app.patch("/internal/users/{user_id}", response_model=UserMeResponse)
def update_any_user_endpoint(
    user_id: str,
    payload: UpdateAnyUserRequest,
    db: Annotated[Session, Depends(get_db)],
) -> UserMeResponse:
    user = update_any_user(user_id, payload, db)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        profile_image_url=user.profile_image_url,
        theme=user.theme,
        language=user.language,
        email_alerts=user.email_alerts,
        sms_urgent_alerts=user.sms_urgent_alerts,
        browser_notifications=user.browser_notifications,
        employee_id=user.employee_id,
        office_location=user.office_location,
    )
