from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserMeResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str


class VerifyTokenRequest(BaseModel):
    token: str


class VerifyTokenResponse(BaseModel):
    sub: str
    role: str
