from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserMeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    profile_image_url: str | None = None
    theme: Literal["light", "dark"] = "light"
    language: str = "es"
    email_alerts: bool = True
    sms_urgent_alerts: bool = True
    browser_notifications: bool = True
    employee_id: str | None = None
    office_location: str | None = None


class UpdateUserMeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    profile_image_url: str | None = Field(default=None, max_length=1024)
    theme: Literal["light", "dark"] | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)
    email_alerts: bool | None = None
    sms_urgent_alerts: bool | None = None
    browser_notifications: bool | None = None
    employee_id: str | None = Field(default=None, max_length=64)
    office_location: str | None = Field(default=None, max_length=255)


class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    role: Literal["admin", "dispatcher"] = "dispatcher"
    password: str = Field(min_length=6, max_length=128)
    profile_image_url: str | None = Field(default=None, max_length=1024)
    theme: Literal["light", "dark"] = "light"
    language: str = Field(default="es", min_length=2, max_length=8)
    email_alerts: bool = True
    sms_urgent_alerts: bool = True
    browser_notifications: bool = True
    employee_id: str | None = Field(default=None, max_length=64)
    office_location: str | None = Field(default=None, max_length=255)


class UpdateAnyUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: Literal["admin", "dispatcher"] | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    profile_image_url: str | None = Field(default=None, max_length=1024)
    theme: Literal["light", "dark"] | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)
    email_alerts: bool | None = None
    sms_urgent_alerts: bool | None = None
    browser_notifications: bool | None = None
    employee_id: str | None = Field(default=None, max_length=64)
    office_location: str | None = Field(default=None, max_length=255)


class VerifyTokenRequest(BaseModel):
    token: str


class VerifyTokenResponse(BaseModel):
    sub: str
    role: str
