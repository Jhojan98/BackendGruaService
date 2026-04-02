import json
import random
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Truck
from .schemas import LocationResponse, TruckResponse


def _load_seed_trucks() -> list[dict]:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data.get("fleet", {}).get("trucks", [])


def seed_trucks(db: Session) -> None:
    if db.scalar(select(Truck).limit(1)):
        return

    trucks = _load_seed_trucks()
    if not trucks:
        return

    db.add_all(
        [
            Truck(
                id=t["id"],
                unit_number=t["unit_number"],
                truck_type=t["truck_type"],
                status=t.get("status", "Available"),
                lat=t["lat"],
                lng=t["lng"],
            )
            for t in trucks
        ]
    )
    db.commit()


def to_truck_response(truck: Truck) -> TruckResponse:
    return TruckResponse(id=truck.id, unitNumber=truck.unit_number, type=truck.truck_type, status=truck.status)


def to_location_response(truck: Truck) -> LocationResponse:
    return LocationResponse(
        truckId=truck.id,
        unitNumber=truck.unit_number,
        lat=truck.lat,
        lng=truck.lng,
        status=truck.status,
    )


def list_fleet(db: Session) -> list[TruckResponse]:
    return [to_truck_response(truck) for truck in db.scalars(select(Truck)).all()]


def get_truck_or_404(truck_id: str, db: Session) -> Truck:
    truck = db.get(Truck, truck_id)
    if not truck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    return truck


def update_status(truck_id: str, new_status: str, db: Session) -> TruckResponse:
    truck = get_truck_or_404(truck_id, db)
    truck.status = new_status
    db.commit()
    db.refresh(truck)
    return to_truck_response(truck)


def list_locations(db: Session) -> list[LocationResponse]:
    return [to_location_response(truck) for truck in db.scalars(select(Truck)).all()]


def update_random_positions(db: Session) -> list[LocationResponse]:
    trucks = db.scalars(select(Truck)).all()
    payload: list[LocationResponse] = []
    for truck in trucks:
        if truck.status != "Maintenance":
            truck.lat = truck.lat + random.uniform(-0.0005, 0.0005)
            truck.lng = truck.lng + random.uniform(-0.0005, 0.0005)
        payload.append(to_location_response(truck))
    db.commit()
    return payload
