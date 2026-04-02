from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import TripAssignRequest, TripCreate, TripResponse, TripStatusUpdate
from .service import (
    assign_trip,
    create_trip,
    get_trip_or_404,
    list_trips,
    seed_trips,
    to_response,
    update_trip_status,
)

app = FastAPI(title="Dispatch Service", version="1.0.0")

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
        seed_trips(db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "dispatch-service"}


@app.get("/internal/trips", response_model=list[TripResponse])
def trips_list(
    status_filter: str | None = Query(default=None, alias="status"),
    _date: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> list[TripResponse]:
    return list_trips(db=db, status_filter=status_filter)


@app.get("/internal/trips/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: str, db: Annotated[Session, Depends(get_db)]) -> TripResponse:
    return to_response(get_trip_or_404(trip_id, db))


@app.post("/internal/trips", response_model=TripResponse, status_code=201)
def trips_create(payload: TripCreate, db: Annotated[Session, Depends(get_db)]) -> TripResponse:
    return create_trip(payload, db)


@app.put("/internal/trips/{trip_id}/status", response_model=TripResponse)
def trip_status_update(
    trip_id: str,
    payload: TripStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TripResponse:
    return update_trip_status(trip_id, payload, db)


@app.put("/internal/trips/{trip_id}/assign", response_model=TripResponse)
def trip_assign(
    trip_id: str,
    payload: TripAssignRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TripResponse:
    return assign_trip(trip_id, payload, db)
