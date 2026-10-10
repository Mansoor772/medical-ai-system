from datetime import datetime, date

from pydantic import BaseModel, EmailStr


class MedicationCreate(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str
    route: str | None = None
    start_date: date
    end_date: date | None = None
    notes: str | None = None


class MedicationResponse(BaseModel):
    id: int
    patient_id: int
    medicine_name: str
    dosage: str
    frequency: str
    route: str | None
    start_date: date
    end_date: date | None
    prescribed_by: int | None
    is_current: bool
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class MedicationUpdate(BaseModel):
    medicine_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    end_date: date | None = None
    is_current: bool | None = None
    notes: str | None = None


class PatientCreate(BaseModel):
    # Demographics
    name: str
    date_of_birth: date
    gender: str                         # male / female / other
    blood_group: str | None = None
    cnic: str | None = None
    phone: str
    email: EmailStr | None = None
    password: str | None = None         # if provided, patient can log in to chatbot
    address: str | None = None

    # Emergency contact
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: str | None = None

    # Medical history
    past_diseases: list[str] | None = None
    past_surgeries: list[str] | None = None
    allergies: list[str] | None = None
    family_history: str | None = None

    # Initial medications (optional at registration)
    medications: list[MedicationCreate] | None = None


class PatientDemographicsUpdate(BaseModel):
    """Super admin editable fields."""
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: str | None = None


class PatientMedicalHistoryUpdate(BaseModel):
    """Doctor-only editable fields."""
    past_diseases: list[str] | None = None
    past_surgeries: list[str] | None = None
    allergies: list[str] | None = None
    family_history: str | None = None


class PatientResponse(BaseModel):
    id: int
    name: str
    date_of_birth: date
    gender: str
    blood_group: str | None
    cnic: str | None
    phone: str
    email: str | None
    address: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None
    past_diseases: list | None
    past_surgeries: list | None
    allergies: list | None
    family_history: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PatientListItem(BaseModel):
    id: int
    name: str
    date_of_birth: date
    gender: str
    blood_group: str | None
    phone: str
    cnic: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
