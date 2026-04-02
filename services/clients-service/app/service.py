import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Client, ClientHistory
from .schemas import ClientCreate, ClientHistoryResponse, ClientResponse


def _load_clients_seed() -> tuple[list[dict], list[dict]]:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return [], []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], []

    section = data.get("clients", {})
    return section.get("clients", []), section.get("history", [])


def seed_clients(db: Session) -> None:
    if db.scalar(select(Client).limit(1)):
        return

    clients, history = _load_clients_seed()
    if not clients and not history:
        return

    if clients:
        db.add_all([Client(**c) for c in clients])
    if history:
        db.add_all([ClientHistory(**h) for h in history])
    db.commit()


def to_client_response(client: Client) -> ClientResponse:
    return ClientResponse(id=client.id, name=client.name, membership=client.membership, phone=client.phone)


def list_clients(db: Session) -> list[ClientResponse]:
    return [to_client_response(c) for c in db.scalars(select(Client)).all()]


def create_client(payload: ClientCreate, db: Session) -> ClientResponse:
    client = Client(id=str(uuid4()), name=payload.name, membership=payload.membership, phone=payload.phone)
    db.add(client)
    db.commit()
    db.refresh(client)
    return to_client_response(client)


def get_client_history(client_id: str, db: Session) -> list[ClientHistoryResponse]:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    entries = db.scalars(select(ClientHistory).where(ClientHistory.client_id == client_id)).all()
    return [
        ClientHistoryResponse(
            id=e.id,
            serviceDate=e.service_date,
            description=e.description,
            revenue=e.revenue,
        )
        for e in entries
    ]
