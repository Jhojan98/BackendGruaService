from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    membership: str
    phone: str


class ClientResponse(BaseModel):
    id: str
    name: str
    membership: str
    phone: str


class ClientHistoryResponse(BaseModel):
    id: str
    serviceDate: str
    description: str
    revenue: float
