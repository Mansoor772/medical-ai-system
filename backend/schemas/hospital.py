from datetime import datetime

from pydantic import BaseModel, EmailStr


class SuperAdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None


class HospitalCreate(BaseModel):
    name: str
    city: str
    address: str | None = None
    contact_email: EmailStr
    contact_phone: str | None = None
    super_admin: SuperAdminCreate


class HospitalUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    address: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None


class HospitalResponse(BaseModel):
    id: int
    name: str
    city: str
    address: str | None
    contact_email: str
    contact_phone: str | None
    db_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HospitalListItem(BaseModel):
    id: int
    name: str
    city: str
    contact_email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
