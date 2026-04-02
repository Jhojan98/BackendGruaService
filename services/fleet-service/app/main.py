import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .schemas import LocationResponse, TruckResponse, TruckStatusUpdate
from .service import (
    get_truck_or_404,
    list_fleet,
    list_locations,
    seed_trucks,
    to_truck_response,
    update_random_positions,
    update_status,
)

app = FastAPI(title="Fleet Service", version="1.0.0")

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
        seed_trucks(db)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "fleet-service"}


@app.get("/internal/fleet", response_model=list[TruckResponse])
def fleet_list(db: Annotated[Session, Depends(get_db)]) -> list[TruckResponse]:
    return list_fleet(db)


@app.get("/internal/fleet/locations", response_model=list[LocationResponse])
def fleet_locations(db: Annotated[Session, Depends(get_db)]) -> list[LocationResponse]:
    return list_locations(db)


@app.get("/internal/fleet/{truck_id}", response_model=TruckResponse)
def get_truck(truck_id: str, db: Annotated[Session, Depends(get_db)]) -> TruckResponse:
    return to_truck_response(get_truck_or_404(truck_id, db))


@app.put("/internal/fleet/{truck_id}/status", response_model=TruckResponse)
def update_truck_status(
    truck_id: str,
    payload: TruckStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> TruckResponse:
    return update_status(truck_id, payload.status, db)


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
