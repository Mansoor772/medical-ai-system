from datetime import datetime

from pydantic import BaseModel, EmailStr


class SuperAdminProfile(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    class Config:
        from_attributes = True


class SuperAdminUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
