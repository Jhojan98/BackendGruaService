from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import ClientCreate, ClientHistoryResponse, ClientResponse
from .service import create_client, get_client_history, list_clients, seed_clients

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
        seed_clients(db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "clients-service"}


@app.get("/internal/clients", response_model=list[ClientResponse])
def clients_list(db: Annotated[Session, Depends(get_db)]) -> list[ClientResponse]:
    return list_clients(db)


@app.post("/internal/clients", response_model=ClientResponse, status_code=201)
def clients_create(payload: ClientCreate, db: Annotated[Session, Depends(get_db)]) -> ClientResponse:
    return create_client(payload, db)


@app.get("/internal/clients/{client_id}/history", response_model=list[ClientHistoryResponse])
def client_history(client_id: str, db: Annotated[Session, Depends(get_db)]) -> list[ClientHistoryResponse]:
    return get_client_history(client_id, db)
