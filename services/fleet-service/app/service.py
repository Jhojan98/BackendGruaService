import json
import random
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Driver, Trip, Truck
from .schemas import (
    DriverCreate,
    DriverResponse,
    DriverUpdate,
    LocationResponse,
    TripAssignRequest,
    TripCreate,
    TripResponse,
    TripStatusUpdate,
    TruckCreate,
    TruckDriverAssignRequest,
    TruckDetailResponse,
    TruckResponse,
    TruckStatusUpdate,
    TruckUpdate,
)


def _load_seed_data() -> dict:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return {}
    try:
        return json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _seed_drivers_from_data(seed: dict, db: Session) -> None:
    if db.scalar(select(Driver).limit(1)):
        return

    seed_drivers = seed.get("drivers", {}).get("drivers")
    if not isinstance(seed_drivers, list):
        seed_drivers = []

    db.add_all(
        [
            Driver(
                id=item.get("id") or str(uuid4()),
                name=item["name"],
                role=item["role"],
                unit=item["unit"],
                status=item.get("status", "Available"),
                shift=item.get("shift", "Morning"),
                phone=item["phone"],
                score=float(item.get("score", 4.5)),
                trips=int(item.get("trips", 0)),
                image_url=item.get("image_url") or item.get("image"),
            )
            for item in seed_drivers
        ]
    )


def _seed_trucks_from_data(seed: dict, db: Session) -> None:
    if db.scalar(select(Truck).limit(1)):
        return

    trucks = seed.get("fleet", {}).get("trucks", [])
    if not isinstance(trucks, list):
        trucks = []

    for item in trucks:
        unit_number = item["unit_number"]
        driver = db.scalar(select(Driver).where(Driver.unit == unit_number).limit(1))
        db.add(
            Truck(
                id=item["id"],
                unit_number=unit_number,
                truck_type=item["truck_type"],
                status=item.get("status", "Available"),
                lat=item.get("lat", 0.0),
                lng=item.get("lng", 0.0),
                driver_id=driver.id if driver else None,
            )
        )


def _seed_trips_from_data(seed: dict, db: Session) -> None:
    if db.scalar(select(Trip).limit(1)):
        return

    trips = seed.get("dispatch", {}).get("trips", [])
    if not isinstance(trips, list):
        trips = []

    db.add_all(
        [
            Trip(
                id=item["id"],
                client_id=item["client_id"],
                client_name=item["client_name"],
                origin=item["origin"],
                destination=item["destination"],
                distance=item.get("distance", "0 km"),
                status=item.get("status", "Pending"),
                tow_truck=item.get("tow_truck", "Unassigned"),
                date=item["date"],
                time=item["time"],
            )
            for item in trips
        ]
    )


def seed_data(db: Session) -> None:
    seed = _load_seed_data()
    _seed_drivers_from_data(seed, db)
    _seed_trucks_from_data(seed, db)
    _seed_trips_from_data(seed, db)
    db.commit()


def _to_driver_response(driver: Driver) -> DriverResponse:
    unit = driver.unit
    if driver.truck is not None:
        unit = driver.truck.unit_number
    return DriverResponse(
        id=driver.id,
        name=driver.name,
        role=driver.role,
        unit=unit,
        status=driver.status,
        shift=driver.shift,
        phone=driver.phone,
        score=driver.score,
        trips=driver.trips,
        image=driver.image_url,
        assignedTruckId=driver.truck.id if driver.truck is not None else None,
        assignedTruckUnit=driver.truck.unit_number if driver.truck is not None else None,
        assignedTruckType=driver.truck.truck_type if driver.truck is not None else None,
        assignedTruckStatus=driver.truck.status if driver.truck is not None else None,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
    )


def _to_truck_response(truck: Truck) -> TruckResponse:
    return TruckResponse(
        id=truck.id,
        unitNumber=truck.unit_number,
        type=truck.truck_type,
        status=truck.status,
        imageUrl=truck.image_url,
        assignedDriverId=truck.driver.id if truck.driver is not None else None,
        assignedDriverName=truck.driver.name if truck.driver is not None else None,
        assignedDriverStatus=truck.driver.status if truck.driver is not None else None,
        assignedDriverImage=truck.driver.image_url if truck.driver is not None else None,
    )


def _to_truck_detail_response(truck: Truck) -> TruckDetailResponse:
    return TruckDetailResponse(
        id=truck.id,
        unitNumber=truck.unit_number,
        type=truck.truck_type,
        status=truck.status,
        imageUrl=truck.image_url,
        assignedDriverId=truck.driver.id if truck.driver is not None else None,
        assignedDriverName=truck.driver.name if truck.driver is not None else None,
        assignedDriverStatus=truck.driver.status if truck.driver is not None else None,
        assignedDriverImage=truck.driver.image_url if truck.driver is not None else None,
        lat=truck.lat,
        lng=truck.lng,
    )


def _to_location_response(truck: Truck) -> LocationResponse:
    return LocationResponse(
        truckId=truck.id,
        unitNumber=truck.unit_number,
        lat=truck.lat,
        lng=truck.lng,
        status=truck.status,
    )


def _to_trip_response(trip: Trip) -> TripResponse:
    return TripResponse(
        id=trip.id,
        clientId=trip.client_id,
        clientName=trip.client_name,
        origin=trip.origin,
        destination=trip.destination,
        distance=trip.distance,
        status=trip.status,
        towTruck=trip.tow_truck,
        date=trip.date,
        time=trip.time,
        driverId=trip.assigned_driver_id,
        driverName=trip.assigned_driver_name,
    )


def list_drivers(
    db: Session,
    *,
    status_filter: str | None = None,
    shift_filter: str | None = None,
    unit_filter: str | None = None,
    search: str | None = None,
) -> list[DriverResponse]:
    stmt = select(Driver)
    if status_filter:
        stmt = stmt.where(Driver.status == status_filter)
    if shift_filter:
        stmt = stmt.where(Driver.shift == shift_filter)
    if unit_filter:
        stmt = stmt.where(Driver.unit == unit_filter)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Driver.id.ilike(pattern),
                Driver.name.ilike(pattern),
                Driver.role.ilike(pattern),
                Driver.unit.ilike(pattern),
                Driver.phone.ilike(pattern),
            )
        )
    stmt = stmt.order_by(Driver.name)
    return [_to_driver_response(driver) for driver in db.scalars(stmt).all()]


def get_driver_or_404(driver_id: str, db: Session) -> Driver:
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


def get_driver(driver_id: str, db: Session) -> DriverResponse:
    return _to_driver_response(get_driver_or_404(driver_id, db))


def _sync_driver_unit_assignment(driver: Driver, db: Session) -> None:
    truck = db.scalar(select(Truck).where(Truck.driver_id == driver.id).limit(1))
    if truck is not None:
        driver.unit = truck.unit_number


def _bind_driver_to_unit(driver: Driver, unit_number: str, db: Session) -> None:
    current_truck = db.scalar(select(Truck).where(Truck.driver_id == driver.id).limit(1))
    target_truck = db.scalar(select(Truck).where(Truck.unit_number == unit_number).limit(1))

    if target_truck is None:
        if current_truck is not None:
            current_truck.driver_id = None
        driver.unit = unit_number
        return

    if target_truck.driver_id is not None and target_truck.driver_id != driver.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Truck already has an assigned driver")

    if current_truck is not None and current_truck.id != target_truck.id:
        current_truck.driver_id = None

    target_truck.driver_id = driver.id
    driver.unit = target_truck.unit_number


def create_driver(payload: DriverCreate, db: Session) -> DriverResponse:
    driver = Driver(
        id=str(uuid4()),
        name=payload.name,
        role=payload.role,
        unit=payload.unit,
        status=payload.status,
        shift=payload.shift,
        phone=payload.phone,
        score=payload.score,
        trips=payload.trips,
        image_url=payload.image_url,
    )
    db.add(driver)
    _bind_driver_to_unit(driver, payload.unit, db)
    db.commit()
    db.refresh(driver)
    return _to_driver_response(driver)


def update_driver(driver_id: str, payload: DriverUpdate, db: Session) -> DriverResponse:
    driver = get_driver_or_404(driver_id, db)
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    new_unit = update_data.pop("unit", None)

    for key, value in update_data.items():
        setattr(driver, key, value)

    if isinstance(new_unit, str):
        _bind_driver_to_unit(driver, new_unit, db)

    _sync_driver_unit_assignment(driver, db)
    db.commit()
    db.refresh(driver)
    return _to_driver_response(driver)


def list_fleet(db: Session) -> list[TruckResponse]:
    return [_to_truck_response(truck) for truck in db.scalars(select(Truck)).all()]


def list_locations(db: Session) -> list[LocationResponse]:
    return [_to_location_response(truck) for truck in db.scalars(select(Truck)).all()]


def update_random_positions(db: Session) -> list[LocationResponse]:
    trucks = db.scalars(select(Truck)).all()
    payload: list[LocationResponse] = []
    for truck in trucks:
        if truck.status != "Maintenance":
            truck.lat = truck.lat + random.uniform(-0.0005, 0.0005)
            truck.lng = truck.lng + random.uniform(-0.0005, 0.0005)
        payload.append(_to_location_response(truck))
    db.commit()
    return payload


def get_truck_or_404(truck_id: str, db: Session) -> Truck:
    truck = db.get(Truck, truck_id)
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Truck not found")
    return truck


def get_truck(truck_id: str, db: Session) -> TruckDetailResponse:
    return _to_truck_detail_response(get_truck_or_404(truck_id, db))


def create_truck(payload: TruckCreate, db: Session) -> TruckResponse:
    existing = db.scalar(select(Truck).where(Truck.unit_number == payload.unit_number))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Truck unit already exists")

    truck = Truck(
        id=str(uuid4()),
        unit_number=payload.unit_number,
        truck_type=payload.truck_type,
        status=payload.status,
        image_url=payload.image_url,
        lat=payload.lat,
        lng=payload.lng,
    )

    matched_driver = db.scalar(select(Driver).where(Driver.unit == payload.unit_number).limit(1))
    if matched_driver is not None and db.scalar(select(Truck).where(Truck.driver_id == matched_driver.id).limit(1)) is None:
        truck.driver_id = matched_driver.id

    db.add(truck)
    db.commit()
    db.refresh(truck)
    return _to_truck_response(truck)


def update_truck(truck_id: str, payload: TruckUpdate, db: Session) -> TruckResponse:
    truck = get_truck_or_404(truck_id, db)
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    new_unit = updates.get("unit_number")
    if isinstance(new_unit, str) and new_unit != truck.unit_number:
        duplicate = db.scalar(select(Truck).where(Truck.unit_number == new_unit))
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Truck unit already exists")

    for field, value in updates.items():
        setattr(truck, field, value)

    if truck.driver is not None:
        truck.driver.unit = truck.unit_number

    db.commit()
    db.refresh(truck)
    return _to_truck_response(truck)


def update_truck_status(truck_id: str, payload: TruckStatusUpdate, db: Session) -> TruckResponse:
    truck = get_truck_or_404(truck_id, db)
    truck.status = payload.status
    db.commit()
    db.refresh(truck)
    return _to_truck_response(truck)


def list_trips(db: Session, status_filter: str | None = None) -> list[TripResponse]:
    stmt = select(Trip)
    if status_filter:
        stmt = stmt.where(Trip.status == status_filter)
    return [_to_trip_response(trip) for trip in db.scalars(stmt).all()]


def get_trip_or_404(trip_id: str, db: Session) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


def get_trip(trip_id: str, db: Session) -> TripResponse:
    return _to_trip_response(get_trip_or_404(trip_id, db))


def _client_exists(client_id: str) -> bool:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{settings.clients_service_url}/internal/clients")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clients service unavailable",
        ) from exc

    if not isinstance(payload, list):
        return False
    return any(isinstance(item, dict) and item.get("id") == client_id for item in payload)


def create_trip(payload: TripCreate, db: Session) -> TripResponse:
    if not _client_exists(payload.client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    now = datetime.now()
    trip = Trip(
        id=str(uuid4()),
        client_id=payload.client_id,
        client_name=payload.client_name or "Unknown Client",
        origin=payload.origin,
        destination=payload.destination,
        distance=payload.distance,
        status="Pending",
        tow_truck="Unassigned",
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return _to_trip_response(trip)


def update_trip_status(trip_id: str, payload: TripStatusUpdate, db: Session) -> TripResponse:
    trip = get_trip_or_404(trip_id, db)
    trip.status = payload.status

    truck = db.scalar(select(Truck).where(Truck.unit_number == trip.tow_truck))
    if payload.status == "Completed":
        if truck is not None:
            truck.status = "Available"
            if truck.driver is not None:
                truck.driver.status = "Available"
                truck.driver.trips = truck.driver.trips + 1
        elif trip.assigned_driver_id:
            driver = db.get(Driver, trip.assigned_driver_id)
            if driver is not None:
                driver.status = "Available"
                driver.trips = driver.trips + 1

    db.commit()
    db.refresh(trip)
    return _to_trip_response(trip)


def assign_trip(trip_id: str, payload: TripAssignRequest, db: Session) -> TripResponse:
    trip = get_trip_or_404(trip_id, db)
    truck = db.scalar(select(Truck).where(Truck.unit_number == payload.tow_truck))
    if truck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tow truck not found")
    if truck.status == "Maintenance":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tow truck in maintenance")
    if truck.driver is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No drivers assigned to unit {payload.tow_truck}",
        )

    trip.tow_truck = payload.tow_truck
    trip.status = "In Progress"
    trip.assigned_driver_id = truck.driver.id
    trip.assigned_driver_name = truck.driver.name
    truck.status = "On Trip"
    truck.driver.status = "On Trip"

    db.commit()
    db.refresh(trip)
    return _to_trip_response(trip)


def assign_truck_driver(truck_id: str, payload: TruckDriverAssignRequest, db: Session) -> TruckResponse:
    truck = get_truck_or_404(truck_id, db)
    driver = get_driver_or_404(payload.driver_id, db)

    previous_truck = db.scalar(select(Truck).where(Truck.driver_id == driver.id).limit(1))
    if previous_truck is not None and previous_truck.id != truck.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Driver already assigned to {previous_truck.unit_number}",
        )

    if truck.driver is not None and truck.driver.id != driver.id:
        truck.driver.status = "Available"

    truck.driver_id = driver.id
    driver.unit = truck.unit_number
    if truck.status == "On Trip":
        driver.status = "On Trip"

    db.commit()
    db.refresh(truck)
    return _to_truck_response(truck)


def delete_driver(driver_id: str, db: Session) -> None:
    driver = get_driver_or_404(driver_id, db)

    in_progress_trip = db.scalar(
        select(Trip).where(Trip.assigned_driver_id == driver.id, Trip.status == "In Progress").limit(1)
    )
    if in_progress_trip is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver has an in-progress trip")

    assigned_truck = db.scalar(select(Truck).where(Truck.driver_id == driver.id).limit(1))
    if assigned_truck is not None:
        assigned_truck.driver_id = None

    db.delete(driver)
    db.commit()


def delete_truck(truck_id: str, db: Session) -> None:
    truck = get_truck_or_404(truck_id, db)

    in_progress_trip = db.scalar(
        select(Trip).where(Trip.tow_truck == truck.unit_number, Trip.status == "In Progress").limit(1)
    )
    if in_progress_trip is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Truck has an in-progress trip")

    if truck.driver is not None:
        truck.driver.unit = "Unassigned"
        truck.driver.status = "Available"

    db.delete(truck)
    db.commit()
