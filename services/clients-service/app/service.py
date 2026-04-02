from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Client, ClientHistory
from .schemas import ClientCreate, ClientHistoryResponse, ClientResponse


def seed_clients(db: Session) -> None:
    if db.scalar(select(Client).limit(1)):
        return

    c1 = Client(id="c1", name="Aria Montgomery", membership="Premium", phone="(503) 555-0123")
    c2 = Client(id="c2", name="Ezra Fitz", membership="Standard", phone="(503) 555-0456")
    db.add_all([c1, c2])
    db.add_all(
        [
            ClientHistory(id="h1", client_id="c1", service_date="2026-03-20", description="Flatbed emergency tow", revenue=180.0),
            ClientHistory(id="h2", client_id="c1", service_date="2026-03-26", description="Battery jumpstart", revenue=60.0),
        ]
    )
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
