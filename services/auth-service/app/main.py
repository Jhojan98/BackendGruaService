from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import LoginRequest, TokenResponse, UserMeResponse, VerifyTokenRequest, VerifyTokenResponse
from .security import decode_token
from .service import get_user_me, login_user, seed_users

app = FastAPI(title="Auth Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
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
    return UserMeResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role)
