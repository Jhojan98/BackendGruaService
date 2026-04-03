import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Client, ClientHistory, ClientVehicle
from .schemas import (
    ClientCreate,
    ClientHistoryResponse,
    ClientResponse,
    ClientUpdate,
    ClientVehicleCreate,
    ClientVehicleResponse,
    ClientVehicleUpdate,
)


def _load_clients_seed() -> tuple[list[dict], list[dict], list[dict]]:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return [], []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], []

    section = data.get("clients", {})
    return section.get("clients", []), section.get("history", []), section.get("vehicles", [])


def seed_clients(db: Session) -> None:
    if db.scalar(select(Client).limit(1)):
        return

    clients, history, vehicles = _load_clients_seed()
    if not clients and not history and not vehicles:
        return

    if clients:
        db.add_all([Client(**c) for c in clients])
    if history:
        db.add_all([ClientHistory(**h) for h in history])
    if vehicles:
        db.add_all([ClientVehicle(**v) for v in vehicles])
    db.commit()


def to_client_response(client: Client) -> ClientResponse:
    return ClientResponse(
        id=client.id,
        name=client.name,
        phone=client.phone,
        status=client.status,
        contact_person=client.contact_person,
        email=client.email,
        client_type=client.client_type,
        logo_url=client.logo_url,
        last_service_date=client.last_service_date,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


def to_vehicle_response(vehicle: ClientVehicle) -> ClientVehicleResponse:
    return ClientVehicleResponse(
        id=vehicle.id,
        client_id=vehicle.client_id,
        make=vehicle.make,
        model=vehicle.model,
        license_plate=vehicle.license_plate,
        is_active=vehicle.is_active,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
    )


def list_clients(db: Session) -> list[ClientResponse]:
    return [to_client_response(c) for c in db.scalars(select(Client).order_by(Client.name)).all()]


def create_client(payload: ClientCreate, db: Session) -> ClientResponse:
    client = Client(
        id=str(uuid4()),
        name=payload.name,
        phone=payload.phone,
        status=payload.status,
        contact_person=payload.contact_person,
        email=payload.email,
        client_type=payload.client_type,
        logo_url=payload.logo_url,
        last_service_date=payload.last_service_date,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return to_client_response(client)


def get_client(client_id: str, db: Session) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def update_client(client_id: str, payload: ClientUpdate, db: Session) -> ClientResponse:
    client = get_client(client_id, db)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    for field, value in changes.items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return to_client_response(client)


def get_client_history(client_id: str, db: Session) -> list[ClientHistoryResponse]:
    get_client(client_id, db)

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


def list_client_vehicles(client_id: str, db: Session) -> list[ClientVehicleResponse]:
    get_client(client_id, db)
    vehicles = db.scalars(select(ClientVehicle).where(ClientVehicle.client_id == client_id).order_by(ClientVehicle.created_at)).all()
    return [to_vehicle_response(vehicle) for vehicle in vehicles]


def create_client_vehicle(client_id: str, payload: ClientVehicleCreate, db: Session) -> ClientVehicleResponse:
    get_client(client_id, db)
    vehicle = ClientVehicle(
        id=str(uuid4()),
        client_id=client_id,
        make=payload.make,
        model=payload.model,
        license_plate=payload.license_plate,
        is_active=payload.is_active,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return to_vehicle_response(vehicle)


def update_client_vehicle(client_id: str, vehicle_id: str, payload: ClientVehicleUpdate, db: Session) -> ClientVehicleResponse:
    get_client(client_id, db)
    vehicle = db.get(ClientVehicle, vehicle_id)
    if not vehicle or vehicle.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client vehicle not found")

    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    for field, value in changes.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return to_vehicle_response(vehicle)


def delete_client_vehicle(client_id: str, vehicle_id: str, db: Session) -> None:
    get_client(client_id, db)
    vehicle = db.get(ClientVehicle, vehicle_id)
    if not vehicle or vehicle.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client vehicle not found")

    db.delete(vehicle)
    db.commit()


def delete_client(client_id: str, db: Session) -> None:
    client = get_client(client_id, db)

    history_entries = db.scalars(select(ClientHistory).where(ClientHistory.client_id == client_id)).all()
    for entry in history_entries:
        db.delete(entry)

    vehicles = db.scalars(select(ClientVehicle).where(ClientVehicle.client_id == client_id)).all()
    for vehicle in vehicles:
        db.delete(vehicle)

    db.delete(client)
    db.commit()
