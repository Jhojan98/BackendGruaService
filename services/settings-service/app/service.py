import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import TariffBillingSettings
from .schemas import TariffBillingResponse, TariffBillingUpdate


def load_tariff_seed() -> dict[str, float]:
    seed_path = Path(settings.seed_data_file)
    if not seed_path.exists():
        return {}
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    payload = data.get("settings", {}).get("tariff_billing")
    if not isinstance(payload, dict):
        return {}

    allowed_keys = {
        "heavy_duty_tow",
        "medium_duty_tow",
        "jumpstart",
        "roadside_assist",
        "cost_per_mile",
        "free_distance_threshold",
        "after_hours_surcharge",
        "fuel_surcharge_percent",
        "severe_weather_fee",
    }
    return {key: float(value) for key, value in payload.items() if key in allowed_keys}


def _to_response(item: TariffBillingSettings) -> TariffBillingResponse:
    return TariffBillingResponse(
        id=item.id,
        heavy_duty_tow=item.heavy_duty_tow,
        medium_duty_tow=item.medium_duty_tow,
        jumpstart=item.jumpstart,
        roadside_assist=item.roadside_assist,
        cost_per_mile=item.cost_per_mile,
        free_distance_threshold=item.free_distance_threshold,
        after_hours_surcharge=item.after_hours_surcharge,
        fuel_surcharge_percent=item.fuel_surcharge_percent,
        severe_weather_fee=item.severe_weather_fee,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def get_or_create_settings(db: Session, seed_values: dict[str, float] | None = None) -> TariffBillingSettings:
    existing = db.scalar(select(TariffBillingSettings).limit(1))
    if existing:
        return existing

    created = TariffBillingSettings(id=1, **(seed_values or {}))
    db.add(created)
    db.commit()
    db.refresh(created)
    return created


def get_tariff_billing(db: Session) -> TariffBillingResponse:
    return _to_response(get_or_create_settings(db))


def update_tariff_billing(payload: TariffBillingUpdate, db: Session) -> TariffBillingResponse:
    item = get_or_create_settings(db)
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return _to_response(item)
