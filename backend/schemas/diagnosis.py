from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DiagnosisQuery(BaseModel):
    patient_id: int
    query: str


class CitationSchema(BaseModel):
    book_id: int
    book_title: str
    author: str | None
    page_number: int
    chunk_text: str


class DiagnosisSuggestionResponse(BaseModel):
    diagnosis_id: int
    patient_id: int
    query: str
    ai_suggestion: str
    citations: list[CitationSchema]


class DiagnosisDecision(BaseModel):
    decision: Literal["accepted", "modified"]
    final_diagnosis: str
    modification_note: str | None = None


class DiagnosisResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    query: str
    ai_suggestion: str
    citations: list | None
    decision: str
    final_diagnosis: str | None
    modification_note: str | None
    suggested_at: datetime
    decided_at: datetime | None

    class Config:
        from_attributes = True
