from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    hospital_id: int | None = None
    hospital_name: str | None = None


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    hospital_id: int | None = None
    hospital_name: str | None = None
