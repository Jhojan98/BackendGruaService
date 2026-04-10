from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import TariffBillingResponse, TariffBillingUpdate
from .service import get_or_create_settings, get_tariff_billing, load_tariff_seed, update_tariff_billing

app = FastAPI(title="Settings Service", version="1.0.0")

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
        ensure_tariff_schema(db)
        get_or_create_settings(db, seed_values=load_tariff_seed())


def ensure_tariff_schema(db: Session) -> None:
    statements = [
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS heavy_duty_tow FLOAT DEFAULT 150.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS medium_duty_tow FLOAT DEFAULT 95.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS jumpstart FLOAT DEFAULT 45.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS roadside_assist FLOAT DEFAULT 65.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS cost_per_mile FLOAT DEFAULT 4.5",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS free_distance_threshold FLOAT DEFAULT 5.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS after_hours_surcharge FLOAT DEFAULT 35.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS fuel_surcharge_percent FLOAT DEFAULT 8.5",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS severe_weather_fee FLOAT DEFAULT 50.0",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE tariff_billing_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "UPDATE tariff_billing_settings SET heavy_duty_tow = 150.0 WHERE heavy_duty_tow IS NULL",
        "UPDATE tariff_billing_settings SET medium_duty_tow = 95.0 WHERE medium_duty_tow IS NULL",
        "UPDATE tariff_billing_settings SET jumpstart = 45.0 WHERE jumpstart IS NULL",
        "UPDATE tariff_billing_settings SET roadside_assist = 65.0 WHERE roadside_assist IS NULL",
        "UPDATE tariff_billing_settings SET cost_per_mile = 4.5 WHERE cost_per_mile IS NULL",
        "UPDATE tariff_billing_settings SET free_distance_threshold = 5.0 WHERE free_distance_threshold IS NULL",
        "UPDATE tariff_billing_settings SET after_hours_surcharge = 35.0 WHERE after_hours_surcharge IS NULL",
        "UPDATE tariff_billing_settings SET fuel_surcharge_percent = 8.5 WHERE fuel_surcharge_percent IS NULL",
        "UPDATE tariff_billing_settings SET severe_weather_fee = 50.0 WHERE severe_weather_fee IS NULL",
        "UPDATE tariff_billing_settings SET created_at = NOW() WHERE created_at IS NULL",
        "UPDATE tariff_billing_settings SET updated_at = NOW() WHERE updated_at IS NULL",
    ]

    for statement in statements:
        db.execute(text(statement))
    db.commit()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "settings-service"}


@app.get("/internal/settings/tariff-billing", response_model=TariffBillingResponse)
def tariff_billing_get(db: Annotated[Session, Depends(get_db)]) -> TariffBillingResponse:
    return get_tariff_billing(db)


@app.patch("/internal/settings/tariff-billing", response_model=TariffBillingResponse)
def tariff_billing_patch(payload: TariffBillingUpdate, db: Annotated[Session, Depends(get_db)]) -> TariffBillingResponse:
    return update_tariff_billing(payload, db)
