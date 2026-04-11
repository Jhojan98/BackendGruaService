from datetime import date
import re
from uuid import uuid4
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_service_url: str = "http://auth-service:8001"
    dispatch_service_url: str = "http://dispatch-service:8002"
    fleet_service_url: str = "http://fleet-service:8003"
    clients_service_url: str = "http://clients-service:8004"
    media_service_url: str = "http://media-service:8005"
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"


settings = Settings()
app = FastAPI(title="Grua API Gateway", version="1.0.0")
bearer_scheme = HTTPBearer(auto_error=True)


class LoginBody(BaseModel):
    email: str
    password: str


class CreateTripBody(BaseModel):
    clientId: str
    clientName: str | None = None
    origin: str | None = None
    destination: str | None = None
    originAddress: str | None = None
    destinationAddress: str | None = None
    distance: str = "0 km"


class UpdateTripStatusBody(BaseModel):
    status: str


class AssignTripBody(BaseModel):
    towTruck: str


class CreateFleetBody(BaseModel):
    unitNumber: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=64)
    status: Literal["Available", "On Trip", "Maintenance"] = "Available"
    lat: float = 0.0
    lng: float = 0.0
    image_url: str | None = Field(default=None, max_length=1024)


class UpdateFleetBody(BaseModel):
    unitNumber: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1, max_length=64)
    status: Literal["Available", "On Trip", "Maintenance"] | None = None
    lat: float | None = None
    lng: float | None = None
    image_url: str | None = Field(default=None, max_length=1024)


class UpdateFleetStatusBody(BaseModel):
    status: Literal["Available", "On Trip", "Maintenance"]


class AssignFleetDriverBody(BaseModel):
    driverId: str = Field(min_length=1, max_length=36)


class CreateClientBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=64)
    status: Literal["active", "inactive", "suspended"]
    contact_person: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=5, max_length=255)
    client_type: Literal["corporate", "individual"]
    logo_url: str | None = None
    last_service_date: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError("Invalid email format")
        return normalized

    @field_validator("last_service_date")
    @classmethod
    def validate_last_service_date(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        try:
            date.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("last_service_date must be YYYY-MM-DD") from exc
        return normalized


class UpdateClientBody(BaseModel):
    name: str | None = None
    phone: str | None = None
    status: Literal["active", "inactive", "suspended"] | None = None
    contact_person: str | None = None
    email: str | None = None
    client_type: Literal["corporate", "individual"] | None = None
    logo_url: str | None = None
    last_service_date: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
            raise ValueError("Invalid email format")
        return normalized

    @field_validator("last_service_date")
    @classmethod
    def validate_last_service_date(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        try:
            date.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("last_service_date must be YYYY-MM-DD") from exc
        return normalized


class CreateDriverBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=128)
    unit: str = Field(min_length=1, max_length=64)
    status: Literal["Available", "On Trip", "Off Duty"] = "Available"
    shift: Literal["Morning", "Evening", "Night", "Rotating"] = "Morning"
    phone: str = Field(min_length=3, max_length=64)
    score: float = Field(default=4.5, ge=0, le=5)
    trips: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=1024)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized


class UpdateDriverBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=128)
    unit: str | None = Field(default=None, min_length=1, max_length=64)
    status: Literal["Available", "On Trip", "Off Duty"] | None = None
    shift: Literal["Morning", "Evening", "Night", "Rotating"] | None = None
    phone: str | None = Field(default=None, min_length=3, max_length=64)
    score: float | None = Field(default=None, ge=0, le=5)
    trips: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=1024)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not re.fullmatch(r"^[+()\-\s0-9]{7,20}$", normalized):
            raise ValueError("Invalid phone format")
        return normalized


class CreateClientVehicleBody(BaseModel):
    make: str
    model: str
    license_plate: str
    is_active: bool = True


class UpdateClientVehicleBody(BaseModel):
    make: str | None = None
    model: str | None = None
    license_plate: str | None = None
    is_active: bool | None = None


class UpdateUserMeBody(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    profile_image_url: str | None = None
    theme: Literal["light", "dark"] | None = None
    language: str | None = None
    email_alerts: bool | None = None
    sms_urgent_alerts: bool | None = None
    browser_notifications: bool | None = None
    employee_id: str | None = None
    office_location: str | None = None


class CreateUserBody(BaseModel):
    email: str
    full_name: str
    role: Literal["admin", "dispatcher"] = "dispatcher"
    password: str
    profile_image_url: str | None = None
    theme: Literal["light", "dark"] = "light"
    language: str = "es"
    email_alerts: bool = True
    sms_urgent_alerts: bool = True
    browser_notifications: bool = True
    employee_id: str | None = None
    office_location: str | None = None


class UpdateAnyUserBody(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: Literal["admin", "dispatcher"] | None = None
    password: str | None = None
    profile_image_url: str | None = None
    theme: Literal["light", "dark"] | None = None
    language: str | None = None
    email_alerts: bool | None = None
    sms_urgent_alerts: bool | None = None
    browser_notifications: bool | None = None
    employee_id: str | None = None
    office_location: str | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def forward_json_request(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.request(method=method, url=url, json=body, params=params)
        if response.status_code >= 400:
            detail: str = "Upstream error"
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = payload.get("detail", detail)
                else:
                    detail = str(payload)
            except ValueError:
                if response.text:
                    detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        if response.status_code == status.HTTP_204_NO_CONTENT or not response.content:
            return None
        return response.json()


async def forward_multipart_request(
    url: str,
    files: dict[str, tuple[str, bytes, str]],
    form_data: dict[str, Any] | None = None,
) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url=url, files=files, data=form_data)
        if response.status_code >= 400:
            detail: str = "Upstream error"
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = payload.get("detail", detail)
                else:
                    detail = str(payload)
            except ValueError:
                if response.text:
                    detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


def decode_bearer_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict[str, Any]:
    return decode_bearer_token(credentials.credentials)


def require_admin(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def _parse_bool(raw: str, field_name: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid boolean for {field_name}")


async def _build_user_update_payload(
    request: Request,
    *,
    target_user_id: str,
    uploaded_by: str,
) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    payload_data: dict[str, Any] = {}

    if "multipart/form-data" in content_type:
        form = await request.form()

        raw_file = form.get("file") or form.get("profile_image") or form.get("profileImage")
        if raw_file is not None and hasattr(raw_file, "read") and hasattr(raw_file, "filename"):
            content = await raw_file.read()
            media_data = await forward_multipart_request(
                url=f"{settings.media_service_url}/internal/media/upload",
                files={
                    "file": (
                        raw_file.filename or "profile-image.bin",
                        content,
                        getattr(raw_file, "content_type", None) or "application/octet-stream",
                    )
                },
                form_data={
                    "entity_type": "users",
                    "entity_id": target_user_id,
                    "uploaded_by": uploaded_by,
                    "access_mode": "public",
                },
            )
            payload_data["profile_image_url"] = media_data.get("url")

        text_fields = {
            "email": form.get("email"),
            "full_name": form.get("full_name"),
            "role": form.get("role"),
            "password": form.get("password"),
            "profile_image_url": form.get("profile_image_url"),
            "theme": form.get("theme"),
            "language": form.get("language"),
            "employee_id": form.get("employee_id"),
            "office_location": form.get("office_location"),
        }
        for key, value in text_fields.items():
            if isinstance(value, str) and value != "":
                payload_data[key] = value

        for key in ["email_alerts", "sms_urgent_alerts", "browser_notifications"]:
            value = form.get(key)
            if isinstance(value, str) and value != "":
                payload_data[key] = _parse_bool(value, key)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = body

    return payload_data


def _coerce_client_field(raw: Any) -> Any:
    if isinstance(raw, str):
        value = raw.strip()
        return value if value != "" else None
    return raw


async def _build_client_payload_from_form(request: Request) -> tuple[dict[str, Any], UploadFile | None]:
    form = await request.form()
    raw_file = form.get("file") or form.get("logo") or form.get("logo_image") or form.get("logoImage")
    file_value: UploadFile | None = None
    if raw_file is not None and hasattr(raw_file, "read") and hasattr(raw_file, "filename"):
        file_value = raw_file  # type: ignore[assignment]

    payload_data: dict[str, Any] = {}
    text_fields = [
        "name",
        "phone",
        "status",
        "contact_person",
        "email",
        "client_type",
        "last_service_date",
    ]
    for key in text_fields:
        value = _coerce_client_field(form.get(key))
        if value is not None:
            payload_data[key] = value

    return payload_data, file_value


def _reject_manual_client_logo_url(payload_data: dict[str, Any]) -> None:
    if "logo_url" in payload_data and payload_data.get("logo_url") is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="logo_url cannot be set directly. Upload a logo file instead.",
        )


def _coerce_driver_field(raw: Any) -> Any:
    if isinstance(raw, str):
        value = raw.strip()
        return value if value != "" else None
    return raw


def _normalize_driver_image_fields(payload_data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload_data)
    image_aliases = ["image", "imageUrl", "imageURL", "profile_image_url", "profileImageUrl"]
    for alias in image_aliases:
        value = normalized.pop(alias, None)
        if value is not None and "image_url" not in normalized:
            normalized["image_url"] = value
    return normalized


def _normalize_fleet_image_fields(payload_data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload_data)
    image_aliases = ["image", "imageUrl", "imageURL", "image_file", "imageFile"]
    for alias in image_aliases:
        value = normalized.pop(alias, None)
        if value is not None and "image_url" not in normalized:
            normalized["image_url"] = value
    return normalized


async def _build_fleet_payload_from_form(request: Request) -> tuple[dict[str, Any], UploadFile | None]:
    form = await request.form()
    raw_file = form.get("file") or form.get("image") or form.get("image_file") or form.get("imageFile")
    file_value: UploadFile | None = None
    if raw_file is not None and hasattr(raw_file, "read") and hasattr(raw_file, "filename"):
        file_value = raw_file  # type: ignore[assignment]

    payload_data: dict[str, Any] = {}
    text_fields = ["unitNumber", "type", "status", "lat", "lng", "image_url", "image", "imageUrl"]
    for key in text_fields:
        value = _coerce_driver_field(form.get(key))
        if value is not None:
            payload_data[key] = value

    if "lat" in payload_data:
        try:
            payload_data["lat"] = float(payload_data["lat"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="lat must be a number") from exc

    if "lng" in payload_data:
        try:
            payload_data["lng"] = float(payload_data["lng"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="lng must be a number") from exc

    return _normalize_fleet_image_fields(payload_data), file_value


async def _build_driver_payload_from_form(request: Request) -> tuple[dict[str, Any], UploadFile | None]:
    form = await request.form()
    raw_file = (
        form.get("file")
        or form.get("image")
        or form.get("image_file")
        or form.get("profile_image")
        or form.get("profileImage")
    )
    file_value: UploadFile | None = None
    if raw_file is not None and hasattr(raw_file, "read") and hasattr(raw_file, "filename"):
        file_value = raw_file  # type: ignore[assignment]

    payload_data: dict[str, Any] = {}
    text_fields = [
        "name",
        "role",
        "unit",
        "status",
        "shift",
        "phone",
        "score",
        "trips",
        "image_url",
        "image",
    ]
    for key in text_fields:
        value = _coerce_driver_field(form.get(key))
        if value is not None:
            payload_data[key] = value

    if "score" in payload_data:
        try:
            payload_data["score"] = float(payload_data["score"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="score must be a number") from exc

    if "trips" in payload_data:
        try:
            payload_data["trips"] = int(payload_data["trips"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="trips must be an integer") from exc

    return _normalize_driver_image_fields(payload_data), file_value


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway"}


@app.post("/api/v1/auth/login")
async def login(payload: LoginBody) -> Any:
    return await forward_json_request(
        "POST",
        f"{settings.auth_service_url}/internal/auth/login",
        body=payload.model_dump(),
    )


@app.get("/api/v1/users/me")
async def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    user_id = user.get("sub")
    return await forward_json_request("GET", f"{settings.auth_service_url}/internal/users/me", params={"user_id": user_id})


@app.patch("/api/v1/users/me")
async def update_me(request: Request, user: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    payload_data = await _build_user_update_payload(request, target_user_id=user_id, uploaded_by=user_id)

    try:
        payload = UpdateUserMeBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc
    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    return await forward_json_request(
        "PATCH",
        f"{settings.auth_service_url}/internal/users/me",
        body=update_payload,
        params={"user_id": user_id},
    )


@app.get("/api/v1/users")
async def list_users(_: Annotated[dict[str, Any], Depends(require_admin)]) -> Any:
    return await forward_json_request("GET", f"{settings.auth_service_url}/internal/users")


@app.patch("/api/v1/users/{target_user_id}")
async def update_any_user(
    target_user_id: str,
    request: Request,
    admin_user: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    admin_id = admin_user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    payload_data = await _build_user_update_payload(request, target_user_id=target_user_id, uploaded_by=admin_id)
    try:
        payload = UpdateAnyUserBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    return await forward_json_request(
        "PATCH",
        f"{settings.auth_service_url}/internal/users/{target_user_id}",
        body=update_payload,
    )


@app.post("/api/v1/users", status_code=201)
async def create_user(payload: CreateUserBody, _: Annotated[dict[str, Any], Depends(require_admin)]) -> Any:
    return await forward_json_request(
        "POST",
        f"{settings.auth_service_url}/internal/users",
        body=payload.model_dump(),
    )


@app.get("/api/v1/notifications")
def notifications(_: Annotated[dict[str, Any], Depends(current_user)]) -> dict:
    return {
        "unread": 3,
        "items": [
            {"id": "n1", "type": "active_alert", "message": "New high-priority dispatch pending"},
            {"id": "n2", "type": "maintenance", "message": "Unit-703 requires scheduled inspection"},
        ],
    }


@app.get("/api/v1/dashboard/stats")
async def dashboard_stats(_: Annotated[dict[str, Any], Depends(current_user)]) -> dict:
    trips = await forward_json_request("GET", f"{settings.fleet_service_url}/internal/trips")
    fleet = await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet")
    active_dispatches = len([t for t in trips if t["status"] in ["Pending", "In Progress"]])
    available_units = len([f for f in fleet if f["status"] == "Available"])
    return {
        "totalTripsToday": len(trips),
        "activeDispatches": active_dispatches,
        "availableUnits": {"current": available_units, "total": len(fleet)},
        "totalRevenueToday": 1240.0,
    }


@app.get("/api/v1/dashboard/quick-actions")
def quick_actions(_: Annotated[dict[str, Any], Depends(current_user)]) -> dict:
    return {
        "actions": [
            {"id": "new-trip", "label": "Create New Trip"},
            {"id": "fleet-map", "label": "Open Live Fleet Map"},
            {"id": "assign-pending", "label": "Assign Pending Trips"},
        ]
    }


@app.get("/api/v1/trips")
async def list_trips(
    _: Annotated[dict[str, Any], Depends(current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    date_filter: str | None = Query(default=None, alias="date"),
) -> Any:
    params: dict[str, Any] = {}
    if status_filter:
        params["status"] = status_filter
    if date_filter:
        params["date"] = date_filter
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/trips", params=params)


@app.get("/api/v1/trips/{trip_id}")
async def get_trip(trip_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/trips/{trip_id}")


@app.post("/api/v1/trips")
async def create_trip(payload: CreateTripBody, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    origin = payload.origin or payload.originAddress
    destination = payload.destination or payload.destinationAddress
    if not origin or not destination:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="origin/destination is required")

    normalized = {
        "client_id": payload.clientId,
        "client_name": payload.clientName or "Unknown Client",
        "origin": origin,
        "destination": destination,
        "distance": payload.distance,
    }
    return await forward_json_request("POST", f"{settings.fleet_service_url}/internal/trips", body=normalized)


@app.put("/api/v1/trips/{trip_id}/status")
async def update_trip_status(
    trip_id: str,
    payload: UpdateTripStatusBody,
    _: Annotated[dict[str, Any], Depends(current_user)],
) -> Any:
    return await forward_json_request(
        "PUT",
        f"{settings.fleet_service_url}/internal/trips/{trip_id}/status",
        body=payload.model_dump(),
    )


@app.put("/api/v1/trips/{trip_id}/assign")
async def assign_trip(trip_id: str, payload: AssignTripBody, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    normalized = {"tow_truck": payload.towTruck}
    return await forward_json_request("PUT", f"{settings.fleet_service_url}/internal/trips/{trip_id}/assign", body=normalized)


@app.get("/api/v1/fleet")
async def list_fleet(_: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet")


@app.get("/api/v1/fleet/locations")
async def fleet_locations(_: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet/locations")


@app.get("/api/v1/fleet/{truck_id}")
async def get_fleet_item(truck_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet/{truck_id}")


@app.post("/api/v1/fleet", status_code=201)
async def create_fleet_item(request: Request, user: Annotated[dict[str, Any], Depends(require_admin)]) -> Any:
    admin_id = user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content_type = request.headers.get("content-type", "")
    image_file: UploadFile | None = None
    if "multipart/form-data" in content_type:
        payload_data, image_file = await _build_fleet_payload_from_form(request)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = _normalize_fleet_image_fields(body)

    try:
        payload = CreateFleetBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    created_truck = await forward_json_request(
        "POST",
        f"{settings.fleet_service_url}/internal/fleet",
        body=payload.model_dump(),
    )

    if image_file is not None:
        content = await image_file.read()
        media_data = await forward_multipart_request(
            url=f"{settings.media_service_url}/internal/media/upload",
            files={
                "file": (
                    image_file.filename or f"fleet-truck-{uuid4().hex}.bin",
                    content,
                    image_file.content_type or "application/octet-stream",
                )
            },
            form_data={
                "entity_type": "trucks",
                "entity_id": created_truck["id"],
                "uploaded_by": admin_id,
                "access_mode": "public",
            },
        )
        created_truck = await forward_json_request(
            "PATCH",
            f"{settings.fleet_service_url}/internal/fleet/{created_truck['id']}",
            body={"image_url": media_data.get("url")},
        )

    return created_truck


@app.patch("/api/v1/fleet/{truck_id}")
async def update_fleet_item(
    truck_id: str,
    request: Request,
    user: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    admin_id = user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content_type = request.headers.get("content-type", "")
    image_file: UploadFile | None = None
    if "multipart/form-data" in content_type:
        payload_data, image_file = await _build_fleet_payload_from_form(request)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = _normalize_fleet_image_fields(body)

    try:
        payload = UpdateFleetBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload and image_file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    truck_data: Any = None
    if update_payload:
        truck_data = await forward_json_request(
            "PATCH",
            f"{settings.fleet_service_url}/internal/fleet/{truck_id}",
            body=update_payload,
        )

    if image_file is not None:
        content = await image_file.read()
        media_data = await forward_multipart_request(
            url=f"{settings.media_service_url}/internal/media/upload",
            files={
                "file": (
                    image_file.filename or f"fleet-truck-{uuid4().hex}.bin",
                    content,
                    image_file.content_type or "application/octet-stream",
                )
            },
            form_data={
                "entity_type": "trucks",
                "entity_id": truck_id,
                "uploaded_by": admin_id,
                "access_mode": "public",
            },
        )
        truck_data = await forward_json_request(
            "PATCH",
            f"{settings.fleet_service_url}/internal/fleet/{truck_id}",
            body={"image_url": media_data.get("url")},
        )

    return truck_data


@app.put("/api/v1/fleet/{truck_id}/status")
async def update_fleet_item_status(
    truck_id: str,
    payload: UpdateFleetStatusBody,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    return await forward_json_request(
        "PUT",
        f"{settings.fleet_service_url}/internal/fleet/{truck_id}/status",
        body=payload.model_dump(),
    )


@app.put("/api/v1/fleet/{truck_id}/driver")
async def assign_fleet_driver(
    truck_id: str,
    payload: AssignFleetDriverBody,
    _: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    normalized = {"driver_id": payload.driverId}
    return await forward_json_request(
        "PUT",
        f"{settings.fleet_service_url}/internal/fleet/{truck_id}/driver",
        body=normalized,
    )


@app.delete("/api/v1/fleet/{truck_id}", status_code=204)
async def delete_fleet_item(truck_id: str, _: Annotated[dict[str, Any], Depends(require_admin)]) -> None:
    await forward_json_request("DELETE", f"{settings.fleet_service_url}/internal/fleet/{truck_id}")


@app.get("/api/v1/drivers")
async def list_drivers(
    _: Annotated[dict[str, Any], Depends(current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    shift_filter: str | None = Query(default=None, alias="shift"),
    unit_filter: str | None = Query(default=None, alias="unit"),
    search: str | None = Query(default=None),
) -> Any:
    params: dict[str, Any] = {}
    if status_filter:
        params["status"] = status_filter
    if shift_filter:
        params["shift"] = shift_filter
    if unit_filter:
        params["unit"] = unit_filter
    if search:
        params["search"] = search
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/drivers", params=params)


@app.get("/api/v1/drivers/{driver_id}")
async def get_driver(driver_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/drivers/{driver_id}")


@app.post("/api/v1/drivers", status_code=201)
async def create_driver(request: Request, user: Annotated[dict[str, Any], Depends(require_admin)]) -> Any:
    admin_id = user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content_type = request.headers.get("content-type", "")
    image_file: UploadFile | None = None
    if "multipart/form-data" in content_type:
        payload_data, image_file = await _build_driver_payload_from_form(request)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = _normalize_driver_image_fields(body)

    try:
        payload = CreateDriverBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    created_driver = await forward_json_request(
        "POST",
        f"{settings.fleet_service_url}/internal/drivers",
        body=payload.model_dump(),
    )

    if image_file is not None:
        content = await image_file.read()
        media_data = await forward_multipart_request(
            url=f"{settings.media_service_url}/internal/media/upload",
            files={
                "file": (
                    image_file.filename or f"driver-profile-{uuid4().hex}.bin",
                    content,
                    image_file.content_type or "application/octet-stream",
                )
            },
            form_data={
                "entity_type": "drivers",
                "entity_id": created_driver["id"],
                "uploaded_by": admin_id,
                "access_mode": "public",
            },
        )
        created_driver = await forward_json_request(
            "PATCH",
            f"{settings.fleet_service_url}/internal/drivers/{created_driver['id']}",
            body={"image_url": media_data.get("url")},
        )

    return created_driver


@app.patch("/api/v1/drivers/{driver_id}")
async def update_driver(
    driver_id: str,
    request: Request,
    user: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    admin_id = user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content_type = request.headers.get("content-type", "")
    image_file: UploadFile | None = None
    if "multipart/form-data" in content_type:
        payload_data, image_file = await _build_driver_payload_from_form(request)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = _normalize_driver_image_fields(body)

    try:
        payload = UpdateDriverBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload and image_file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    driver_data: Any = None
    if update_payload:
        driver_data = await forward_json_request(
            "PATCH",
            f"{settings.fleet_service_url}/internal/drivers/{driver_id}",
            body=update_payload,
        )

    if image_file is not None:
        content = await image_file.read()
        media_data = await forward_multipart_request(
            url=f"{settings.media_service_url}/internal/media/upload",
            files={
                "file": (
                    image_file.filename or f"driver-profile-{uuid4().hex}.bin",
                    content,
                    image_file.content_type or "application/octet-stream",
                )
            },
            form_data={
                "entity_type": "drivers",
                "entity_id": driver_id,
                "uploaded_by": admin_id,
                "access_mode": "public",
            },
        )
        driver_data = await forward_json_request(
            "PATCH",
            f"{settings.fleet_service_url}/internal/drivers/{driver_id}",
            body={"image_url": media_data.get("url")},
        )

    return driver_data


@app.delete("/api/v1/drivers/{driver_id}", status_code=204)
async def delete_driver(driver_id: str, _: Annotated[dict[str, Any], Depends(require_admin)]) -> None:
    await forward_json_request("DELETE", f"{settings.fleet_service_url}/internal/drivers/{driver_id}")


@app.get("/api/v1/clients")
async def list_clients(_: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.clients_service_url}/internal/clients")


@app.post("/api/v1/clients", status_code=201)
async def create_client(request: Request, user: Annotated[dict[str, Any], Depends(require_admin)]) -> Any:
    admin_id = user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content_type = request.headers.get("content-type", "")
    logo_file: UploadFile | None = None
    if "multipart/form-data" in content_type:
        payload_data, logo_file = await _build_client_payload_from_form(request)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = body

    _reject_manual_client_logo_url(payload_data)

    try:
        payload = CreateClientBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    created_client = await forward_json_request(
        "POST",
        f"{settings.clients_service_url}/internal/clients",
        body=payload.model_dump(),
    )

    if logo_file is not None:
        content = await logo_file.read()
        media_data = await forward_multipart_request(
            url=f"{settings.media_service_url}/internal/media/upload",
            files={
                "file": (
                    logo_file.filename or f"client-logo-{uuid4().hex}.bin",
                    content,
                    logo_file.content_type or "application/octet-stream",
                )
            },
            form_data={
                "entity_type": "clients",
                "entity_id": created_client["id"],
                "uploaded_by": admin_id,
                "access_mode": "public",
            },
        )
        created_client = await forward_json_request(
            "PATCH",
            f"{settings.clients_service_url}/internal/clients/{created_client['id']}",
            body={"logo_url": media_data.get("url")},
        )

    return created_client


@app.patch("/api/v1/clients/{client_id}")
async def update_client(
    client_id: str,
    request: Request,
    user: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    admin_id = user.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content_type = request.headers.get("content-type", "")
    logo_file: UploadFile | None = None
    if "multipart/form-data" in content_type:
        payload_data, logo_file = await _build_client_payload_from_form(request)
    else:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be an object")
        payload_data = body

    _reject_manual_client_logo_url(payload_data)

    if logo_file is not None:
        content = await logo_file.read()
        media_data = await forward_multipart_request(
            url=f"{settings.media_service_url}/internal/media/upload",
            files={
                "file": (
                    logo_file.filename or f"client-logo-{uuid4().hex}.bin",
                    content,
                    logo_file.content_type or "application/octet-stream",
                )
            },
            form_data={
                "entity_type": "clients",
                "entity_id": client_id,
                "uploaded_by": admin_id,
                "access_mode": "public",
            },
        )
        payload_data["logo_url"] = media_data.get("url")

    try:
        payload = UpdateClientBody(**payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    return await forward_json_request(
        "PATCH",
        f"{settings.clients_service_url}/internal/clients/{client_id}",
        body=update_payload,
    )


@app.delete("/api/v1/clients/{client_id}", status_code=204)
async def delete_client(client_id: str, user: Annotated[dict[str, Any], Depends(require_admin)]) -> None:
    _ = user
    await forward_json_request(
        "DELETE",
        f"{settings.clients_service_url}/internal/clients/{client_id}",
    )


@app.get("/api/v1/clients/{client_id}/history")
async def client_history(client_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.clients_service_url}/internal/clients/{client_id}/history")


@app.get("/api/v1/clients/{client_id}/vehicles")
async def client_vehicles(client_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.clients_service_url}/internal/clients/{client_id}/vehicles")


@app.post("/api/v1/clients/{client_id}/vehicles", status_code=201)
async def create_client_vehicle(
    client_id: str,
    payload: CreateClientVehicleBody,
    user: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    _ = user
    return await forward_json_request(
        "POST",
        f"{settings.clients_service_url}/internal/clients/{client_id}/vehicles",
        body=payload.model_dump(),
    )


@app.patch("/api/v1/clients/{client_id}/vehicles/{vehicle_id}")
async def update_client_vehicle(
    client_id: str,
    vehicle_id: str,
    payload: UpdateClientVehicleBody,
    user: Annotated[dict[str, Any], Depends(require_admin)],
) -> Any:
    _ = user
    update_payload = payload.model_dump(exclude_none=True)
    if not update_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updatable fields provided")

    return await forward_json_request(
        "PATCH",
        f"{settings.clients_service_url}/internal/clients/{client_id}/vehicles/{vehicle_id}",
        body=update_payload,
    )


@app.delete("/api/v1/clients/{client_id}/vehicles/{vehicle_id}", status_code=204)
async def delete_client_vehicle(
    client_id: str,
    vehicle_id: str,
    user: Annotated[dict[str, Any], Depends(require_admin)],
) -> None:
    _ = user
    await forward_json_request(
        "DELETE",
        f"{settings.clients_service_url}/internal/clients/{client_id}/vehicles/{vehicle_id}",
    )


@app.get("/api/v1/analytics/revenue")
def analytics_revenue(
    _: Annotated[dict[str, Any], Depends(current_user)],
    period: str = Query(default="daily"),
) -> dict:
    if period == "monthly":
        points = [{"label": "Jan", "amount": 22100.0}, {"label": "Feb", "amount": 24500.0}, {"label": "Mar", "amount": 23950.0}]
    elif period == "weekly":
        points = [{"label": "W1", "amount": 5200.0}, {"label": "W2", "amount": 6100.0}, {"label": "W3", "amount": 5750.0}]
    else:
        points = [{"label": "Mon", "amount": 820.0}, {"label": "Tue", "amount": 910.0}, {"label": "Wed", "amount": 1240.0}]
    return {"period": period, "data": points}


@app.get("/api/v1/analytics/performance")
def analytics_performance(_: Annotated[dict[str, Any], Depends(current_user)]) -> dict:
    return {
        "avgResponseTime": "18 mins",
        "avgTripDuration": "42 mins",
        "fleetUtilization": 84.2,
        "jobCompletionRate": 96.8,
    }


@app.post("/api/v1/media/upload", status_code=201)
async def media_upload(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    access_mode: str | None = Form(default=None),
    user: dict[str, Any] = Depends(current_user),
) -> Any:
    user_id = user.get("sub") if user else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    content = await file.read()
    files = {
        "file": (
            file.filename or "upload.bin",
            content,
            file.content_type or "application/octet-stream",
        )
    }
    form_data = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "uploaded_by": user_id,
    }
    if access_mode:
        form_data["access_mode"] = access_mode

    return await forward_multipart_request(
        url=f"{settings.media_service_url}/internal/media/upload",
        files=files,
        form_data=form_data,
    )


@app.get("/api/v1/media/by-entity")
async def media_by_entity(
    entity_type: str,
    entity_id: str,
    _: Annotated[dict[str, Any], Depends(current_user)],
) -> Any:
    return await forward_json_request(
        "GET",
        f"{settings.media_service_url}/internal/media/by-entity",
        params={"entity_type": entity_type, "entity_id": entity_id},
    )


@app.get("/api/v1/media/{media_id}")
async def media_get(media_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.media_service_url}/internal/media/{media_id}")
