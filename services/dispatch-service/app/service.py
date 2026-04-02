from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Trip
from .schemas import TripAssignRequest, TripCreate, TripResponse, TripStatusUpdate


def seed_trips(db: Session) -> None:
    if db.scalar(select(Trip).limit(1)):
        return

    now = datetime.now()
    seed = Trip(
        id="trip-1",
        client_id="c1",
        client_name="Aria Montgomery",
        origin="Main St 123",
        destination="7th Ave 90",
        distance="8.4 km",
        status="Pending",
        tow_truck="Unassigned",
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
    )
    db.add(seed)
    db.commit()


def to_response(trip: Trip) -> TripResponse:
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
    )


def list_trips(db: Session, status_filter: str | None = None) -> list[TripResponse]:
    stmt = select(Trip)
    if status_filter:
        stmt = stmt.where(Trip.status == status_filter)
    return [to_response(trip) for trip in db.scalars(stmt).all()]


def get_trip_or_404(trip_id: str, db: Session) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


def create_trip(payload: TripCreate, db: Session) -> TripResponse:
    now = datetime.now()
    trip = Trip(
        id=str(uuid4()),
        client_id=payload.client_id,
        client_name=payload.client_name,
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
    return to_response(trip)


def update_trip_status(trip_id: str, payload: TripStatusUpdate, db: Session) -> TripResponse:
    trip = get_trip_or_404(trip_id, db)
    trip.status = payload.status
    db.commit()
    db.refresh(trip)
    return to_response(trip)


def assign_trip(trip_id: str, payload: TripAssignRequest, db: Session) -> TripResponse:
    trip = get_trip_or_404(trip_id, db)
    trip.tow_truck = payload.tow_truck
    trip.status = "In Progress"
    db.commit()
    db.refresh(trip)
    return to_response(trip)
