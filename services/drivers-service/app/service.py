import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Driver
from .schemas import DriverCreate, DriverResponse, DriverUpdate


def _load_seed_drivers() -> list[dict]:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return []
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    drivers = data.get("drivers", {}).get("drivers")
    if isinstance(drivers, list):
        return drivers

    return [
        {
            "id": "DR-1147",
            "name": "Marcus Reed",
            "role": "Senior Recovery Operator",
            "unit": "Unit-701",
            "status": "Available",
            "shift": "Morning",
            "phone": "+1 (555) 334-8877",
            "score": 4.9,
            "trips": 64,
            "image_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=200&h=200",
        },
        {
            "id": "DR-2019",
            "name": "Elena Rodriguez",
            "role": "Light Duty Specialist",
            "unit": "Unit-203",
            "status": "On Trip",
            "shift": "Evening",
            "phone": "+1 (555) 717-2044",
            "score": 4.8,
            "trips": 58,
            "image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=200&h=200",
        },
        {
            "id": "DR-3091",
            "name": "Noah Kim",
            "role": "Tow Operator",
            "unit": "Unit-412",
            "status": "Off Duty",
            "shift": "Night",
            "phone": "+1 (555) 222-1198",
            "score": 4.7,
            "trips": 49,
            "image_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=200&h=200",
        },
        {
            "id": "DR-4070",
            "name": "Ava Patel",
            "role": "Heavy Duty Operator",
            "unit": "Unit-905",
            "status": "Available",
            "shift": "Rotating",
            "phone": "+1 (555) 980-4412",
            "score": 4.9,
            "trips": 71,
            "image_url": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&q=80&w=200&h=200",
        },
    ]


def to_driver_response(driver: Driver) -> DriverResponse:
    return DriverResponse(
        id=driver.id,
        name=driver.name,
        role=driver.role,
        unit=driver.unit,
        status=driver.status,
        shift=driver.shift,
        phone=driver.phone,
        score=driver.score,
        trips=driver.trips,
        image=driver.image_url,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
    )


def seed_drivers(db: Session) -> None:
    if db.scalar(select(Driver).limit(1)):
        return

    seed_drivers_data = _load_seed_drivers()
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
            for item in seed_drivers_data
        ]
    )
    db.commit()


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
    return [to_driver_response(driver) for driver in db.scalars(stmt).all()]


def get_driver_or_404(driver_id: str, db: Session) -> Driver:
    driver = db.get(Driver, driver_id)
    if not driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


def get_driver(driver_id: str, db: Session) -> DriverResponse:
    return to_driver_response(get_driver_or_404(driver_id, db))


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
    db.commit()
    db.refresh(driver)
    return to_driver_response(driver)


def update_driver(driver_id: str, payload: DriverUpdate, db: Session) -> DriverResponse:
    driver = get_driver_or_404(driver_id, db)
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    for key, value in update_data.items():
        setattr(driver, key, value)

    db.commit()
    db.refresh(driver)
    return to_driver_response(driver)
