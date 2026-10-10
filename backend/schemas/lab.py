from datetime import datetime, date

from pydantic import BaseModel


class LabResultCreate(BaseModel):
    test_name: str
    test_date: date
    result_value: str
    unit: str | None = None
    reference_range: str | None = None
    is_abnormal: bool = False
    notes: str | None = None


class LabResultUpdate(BaseModel):
    result_value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    is_abnormal: bool | None = None
    notes: str | None = None


class LabResultResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    test_name: str
    test_date: date
    result_value: str
    unit: str | None
    reference_range: str | None
    is_abnormal: bool
    notes: str | None
    alert_status: str
    alert_approved_by: int | None
    alert_approved_at: datetime | None
    alert_sent_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
