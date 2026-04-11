import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
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
from .service import (
    assign_trip,
    assign_truck_driver,
    create_driver,
    create_trip,
    create_truck,
    delete_driver,
    delete_truck,
    get_driver,
    get_trip,
    get_truck as svc_get_truck,
    list_drivers,
    list_fleet,
    list_locations,
    list_trips,
    seed_data,
    update_driver,
    update_random_positions,
    update_trip_status,
    update_truck,
    update_truck_status as svc_update_truck_status,
)

app = FastAPI(title="Fleet Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_schema_compatibility() -> None:
    # Keep existing volumes compatible when new columns are introduced.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE trucks ADD COLUMN IF NOT EXISTS image_url VARCHAR(1024)"))
        conn.execute(text("ALTER TABLE trucks ADD COLUMN IF NOT EXISTS driver_id VARCHAR(36)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_trucks_driver_id ON trucks(driver_id) WHERE driver_id IS NOT NULL"))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_schema_compatibility()
    with SessionLocal() as db:
        seed_data(db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "fleet-service"}


@app.get("/internal/drivers", response_model=list[DriverResponse])
def drivers_list(
    status_filter: str | None = Query(default=None, alias="status"),
    shift_filter: str | None = Query(default=None, alias="shift"),
    unit_filter: str | None = Query(default=None, alias="unit"),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
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
def drivers_create(payload: DriverCreate, db: Annotated[Session, Depends(get_db)]) -> DriverResponse:
    return create_driver(payload, db)


@app.patch("/internal/drivers/{driver_id}", response_model=DriverResponse)
def drivers_update(
    driver_id: str,
    payload: DriverUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> DriverResponse:
    return update_driver(driver_id, payload, db)


@app.delete("/internal/drivers/{driver_id}", status_code=204)
def drivers_delete(driver_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    delete_driver(driver_id, db)


@app.get("/internal/fleet", response_model=list[TruckResponse])
def fleet_list(db: Annotated[Session, Depends(get_db)]) -> list[TruckResponse]:
    return list_fleet(db)


@app.get("/internal/fleet/locations", response_model=list[LocationResponse])
def fleet_locations(db: Annotated[Session, Depends(get_db)]) -> list[LocationResponse]:
    return list_locations(db)


@app.get("/internal/fleet/{truck_id}", response_model=TruckDetailResponse)
def get_truck(truck_id: str, db: Annotated[Session, Depends(get_db)]) -> TruckDetailResponse:
    return svc_get_truck(truck_id, db)


@app.post("/internal/fleet", response_model=TruckResponse, status_code=201)
def fleet_create(payload: TruckCreate, db: Annotated[Session, Depends(get_db)]) -> TruckResponse:
    return create_truck(payload, db)


@app.patch("/internal/fleet/{truck_id}", response_model=TruckResponse)
def fleet_update(truck_id: str, payload: TruckUpdate, db: Annotated[Session, Depends(get_db)]) -> TruckResponse:
    return update_truck(truck_id, payload, db)


@app.delete("/internal/fleet/{truck_id}", status_code=204)
def fleet_delete(truck_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    delete_truck(truck_id, db)


@app.put("/internal/fleet/{truck_id}/driver", response_model=TruckResponse)
def fleet_assign_driver(
    truck_id: str,
    payload: TruckDriverAssignRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TruckResponse:
    return assign_truck_driver(truck_id, payload, db)


@app.put("/internal/fleet/{truck_id}/status", response_model=TruckResponse)
def update_truck_status(
    truck_id: str,
    payload: TruckStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TruckResponse:
    return svc_update_truck_status(truck_id, payload, db)


@app.get("/internal/trips", response_model=list[TripResponse])
def trips_list(
    status_filter: str | None = Query(default=None, alias="status"),
    _date: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> list[TripResponse]:
    return list_trips(db=db, status_filter=status_filter)


@app.get("/internal/trips/{trip_id}", response_model=TripResponse)
def trip_detail(trip_id: str, db: Annotated[Session, Depends(get_db)]) -> TripResponse:
    return get_trip(trip_id, db)


@app.post("/internal/trips", response_model=TripResponse, status_code=201)
def trip_create(payload: TripCreate, db: Annotated[Session, Depends(get_db)]) -> TripResponse:
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


@app.websocket("/ws/locations")
async def stream_locations(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            with SessionLocal() as db:
                payload = [item.model_dump() for item in update_random_positions(db)]
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
