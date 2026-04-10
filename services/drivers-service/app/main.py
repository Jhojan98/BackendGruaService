from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import DriverCreate, DriverResponse, DriverShift, DriverStatus, DriverUpdate
from .service import create_driver, get_driver, list_drivers, seed_drivers, update_driver

app = FastAPI(title="Drivers Service", version="1.0.0")

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
        ensure_driver_schema(db)
        seed_drivers(db)


def ensure_driver_schema(db: Session) -> None:
    statements = [
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS role VARCHAR(128) DEFAULT 'Tow Operator'",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS unit VARCHAR(64) DEFAULT 'Unassigned'",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'Available'",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS shift VARCHAR(32) DEFAULT 'Morning'",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS phone VARCHAR(64) DEFAULT '(000) 000-0000'",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS score FLOAT DEFAULT 4.5",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS trips INTEGER DEFAULT 0",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS image_url VARCHAR(1024)",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "UPDATE drivers SET role = 'Tow Operator' WHERE role IS NULL",
        "UPDATE drivers SET unit = 'Unassigned' WHERE unit IS NULL",
        "UPDATE drivers SET status = 'Available' WHERE status IS NULL",
        "UPDATE drivers SET shift = 'Morning' WHERE shift IS NULL",
        "UPDATE drivers SET phone = '(000) 000-0000' WHERE phone IS NULL",
        "UPDATE drivers SET score = 4.5 WHERE score IS NULL",
        "UPDATE drivers SET trips = 0 WHERE trips IS NULL",
        "UPDATE drivers SET created_at = NOW() WHERE created_at IS NULL",
        "UPDATE drivers SET updated_at = NOW() WHERE updated_at IS NULL",
    ]

    for statement in statements:
        db.execute(text(statement))
    db.commit()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "drivers-service"}


@app.get("/internal/drivers", response_model=list[DriverResponse])
def drivers_list(
    db: Annotated[Session, Depends(get_db)],
    status_filter: DriverStatus | None = Query(default=None, alias="status"),
    shift_filter: DriverShift | None = Query(default=None, alias="shift"),
    unit_filter: str | None = Query(default=None, alias="unit"),
    search: str | None = Query(default=None),
) -> list[DriverResponse]:
    return list_drivers(
        db,
        status_filter=status_filter,
        shift_filter=shift_filter,
        unit_filter=unit_filter,
        search=search,
    )


@app.get("/internal/drivers/{driver_id}", response_model=DriverResponse)
def driver_detail(driver_id: str, db: Annotated[Session, Depends(get_db)]) -> DriverResponse:
    return get_driver(driver_id, db)


@app.post("/internal/drivers", response_model=DriverResponse, status_code=201)
def driver_create(payload: DriverCreate, db: Annotated[Session, Depends(get_db)]) -> DriverResponse:
    return create_driver(payload, db)


@app.patch("/internal/drivers/{driver_id}", response_model=DriverResponse)
def driver_update(driver_id: str, payload: DriverUpdate, db: Annotated[Session, Depends(get_db)]) -> DriverResponse:
    return update_driver(driver_id, payload, db)
