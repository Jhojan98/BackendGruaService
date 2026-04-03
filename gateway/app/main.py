from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
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


class CreateClientBody(BaseModel):
    name: str
    membership: str
    phone: str

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
    trips = await forward_json_request("GET", f"{settings.dispatch_service_url}/internal/trips")
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
    return await forward_json_request("GET", f"{settings.dispatch_service_url}/internal/trips", params=params)


@app.get("/api/v1/trips/{trip_id}")
async def get_trip(trip_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.dispatch_service_url}/internal/trips/{trip_id}")


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
    return await forward_json_request("POST", f"{settings.dispatch_service_url}/internal/trips", body=normalized)


@app.put("/api/v1/trips/{trip_id}/status")
async def update_trip_status(
    trip_id: str,
    payload: UpdateTripStatusBody,
    _: Annotated[dict[str, Any], Depends(current_user)],
) -> Any:
    return await forward_json_request(
        "PUT",
        f"{settings.dispatch_service_url}/internal/trips/{trip_id}/status",
        body=payload.model_dump(),
    )


@app.put("/api/v1/trips/{trip_id}/assign")
async def assign_trip(trip_id: str, payload: AssignTripBody, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    normalized = {"tow_truck": payload.towTruck}
    return await forward_json_request("PUT", f"{settings.dispatch_service_url}/internal/trips/{trip_id}/assign", body=normalized)


@app.get("/api/v1/fleet")
async def list_fleet(_: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet")


@app.get("/api/v1/fleet/locations")
async def fleet_locations(_: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet/locations")


@app.get("/api/v1/fleet/{truck_id}")
async def get_fleet_item(truck_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.fleet_service_url}/internal/fleet/{truck_id}")


@app.get("/api/v1/clients")
async def list_clients(_: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.clients_service_url}/internal/clients")


@app.post("/api/v1/clients")
async def create_client(payload: CreateClientBody, user: Annotated[dict[str, Any], Depends(require_admin)]) -> Any:
    _ = user
    return await forward_json_request(
        "POST",
        f"{settings.clients_service_url}/internal/clients",
        body=payload.model_dump(),
    )


@app.get("/api/v1/clients/{client_id}/history")
async def client_history(client_id: str, _: Annotated[dict[str, Any], Depends(current_user)]) -> Any:
    return await forward_json_request("GET", f"{settings.clients_service_url}/internal/clients/{client_id}/history")


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
