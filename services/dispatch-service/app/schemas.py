from pydantic import BaseModel


class TripCreate(BaseModel):
    client_id: str
    client_name: str
    origin: str
    destination: str
    distance: str = "0 km"


class TripStatusUpdate(BaseModel):
    status: str


class TripAssignRequest(BaseModel):
    tow_truck: str


class TripResponse(BaseModel):
    id: str
    clientId: str
    clientName: str
    origin: str
    destination: str
    distance: str
    status: str
    towTruck: str
    date: str
    time: str
