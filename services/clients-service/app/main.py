from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import (
    ClientCreate,
    ClientHistoryResponse,
    ClientResponse,
    ClientUpdate,
    ClientVehicleCreate,
    ClientVehicleResponse,
    ClientVehicleUpdate,
)
from .service import (
    create_client,
    create_client_vehicle,
    delete_client,
    delete_client_vehicle,
    get_client_history,
    list_client_vehicles,
    list_clients,
    seed_clients,
    update_client,
    update_client_vehicle,
)

app = FastAPI(title="Clients Service", version="1.0.0")

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
        ensure_client_schema(db)
        seed_clients(db)


def ensure_client_schema(db: Session) -> None:
    statements = [
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS membership VARCHAR(64) DEFAULT 'standard'",
        "ALTER TABLE clients ALTER COLUMN membership SET DEFAULT 'standard'",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS status VARCHAR(16) DEFAULT 'active'",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS contact_person VARCHAR(255)",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS client_type VARCHAR(32) DEFAULT 'corporate'",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS logo_url VARCHAR(1024)",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_service_date VARCHAR(16)",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "UPDATE clients SET status = 'active' WHERE status IS NULL",
        "UPDATE clients SET membership = 'standard' WHERE membership IS NULL",
        "UPDATE clients SET client_type = 'corporate' WHERE client_type IS NULL",
        "UPDATE clients SET created_at = NOW() WHERE created_at IS NULL",
        "UPDATE clients SET updated_at = NOW() WHERE updated_at IS NULL",
        "CREATE TABLE IF NOT EXISTS client_vehicles ("
        "id VARCHAR(36) PRIMARY KEY, "
        "client_id VARCHAR(36) NOT NULL REFERENCES clients(id) ON DELETE CASCADE, "
        "make VARCHAR(128) NOT NULL, "
        "model VARCHAR(128) NOT NULL, "
        "license_plate VARCHAR(32) NOT NULL, "
        "is_active BOOLEAN DEFAULT TRUE, "
        "created_at TIMESTAMPTZ DEFAULT NOW(), "
        "updated_at TIMESTAMPTZ DEFAULT NOW()"
        ")",
        "CREATE INDEX IF NOT EXISTS ix_client_vehicles_client_id ON client_vehicles (client_id)",
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "clients-service"}


@app.get("/internal/clients", response_model=list[ClientResponse])
def clients_list(db: Annotated[Session, Depends(get_db)]) -> list[ClientResponse]:
    return list_clients(db)


@app.post("/internal/clients", response_model=ClientResponse, status_code=201)
def clients_create(payload: ClientCreate, db: Annotated[Session, Depends(get_db)]) -> ClientResponse:
    return create_client(payload, db)


@app.patch("/internal/clients/{client_id}", response_model=ClientResponse)
def clients_update(client_id: str, payload: ClientUpdate, db: Annotated[Session, Depends(get_db)]) -> ClientResponse:
    return update_client(client_id, payload, db)


@app.delete("/internal/clients/{client_id}", status_code=204)
def clients_delete(client_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    delete_client(client_id, db)


@app.get("/internal/clients/{client_id}/history", response_model=list[ClientHistoryResponse])
def client_history(client_id: str, db: Annotated[Session, Depends(get_db)]) -> list[ClientHistoryResponse]:
    return get_client_history(client_id, db)


@app.get("/internal/clients/{client_id}/vehicles", response_model=list[ClientVehicleResponse])
def client_vehicles_list(client_id: str, db: Annotated[Session, Depends(get_db)]) -> list[ClientVehicleResponse]:
    return list_client_vehicles(client_id, db)


@app.post("/internal/clients/{client_id}/vehicles", response_model=ClientVehicleResponse, status_code=201)
def client_vehicles_create(
    client_id: str,
    payload: ClientVehicleCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ClientVehicleResponse:
    return create_client_vehicle(client_id, payload, db)


@app.patch("/internal/clients/{client_id}/vehicles/{vehicle_id}", response_model=ClientVehicleResponse)
def client_vehicles_update(
    client_id: str,
    vehicle_id: str,
    payload: ClientVehicleUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> ClientVehicleResponse:
    return update_client_vehicle(client_id, vehicle_id, payload, db)


@app.delete("/internal/clients/{client_id}/vehicles/{vehicle_id}", status_code=204)
def client_vehicles_delete(client_id: str, vehicle_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    delete_client_vehicle(client_id, vehicle_id, db)
