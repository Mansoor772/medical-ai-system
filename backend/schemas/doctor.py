from datetime import datetime

from pydantic import BaseModel, EmailStr


class DoctorCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    license_number: str
    specialization: str
    qualification: str | None = None


class DoctorUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    specialization: str | None = None
    qualification: str | None = None


class DoctorResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    license_number: str
    specialization: str
    qualification: str | None
    is_active: bool
    created_at: datetime
    last_login: datetime | None

    class Config:
        from_attributes = True


class DoctorListItem(BaseModel):
    id: int
    name: str
    email: str
    specialization: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
