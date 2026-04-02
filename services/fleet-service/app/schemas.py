from pydantic import BaseModel


class TruckResponse(BaseModel):
    id: str
    unitNumber: str
    type: str
    status: str


class LocationResponse(BaseModel):
    truckId: str
    unitNumber: str
    lat: float
    lng: float
    status: str


class TruckStatusUpdate(BaseModel):
    status: str
