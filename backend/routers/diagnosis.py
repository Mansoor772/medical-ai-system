from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_tenant_session
from core.llm import generate_diagnosis_suggestion
from core.rag import retrieve_chunks
from models.tenant_models import AuditLog, Diagnosis, Medication, Patient
from schemas.diagnosis import (
    DiagnosisDecision,
    DiagnosisQuery,
    DiagnosisResponse,
    DiagnosisSuggestionResponse,
    CitationSchema,
)

router = APIRouter(prefix="/diagnosis", tags=["Diagnosis"])


def _require_doctor(user: dict) -> dict:
    if user.get("role") != "doctor":
        raise HTTPException(status_code=403, detail="Doctor access required")
    return user


@router.post("/query", response_model=DiagnosisSuggestionResponse)
def query_diagnosis(
    body: DiagnosisQuery,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    """Doctor queries the RAG system about a patient. Returns an advisory suggestion with citations."""
    _require_doctor(user)

    patient = db.query(Patient).filter(
        Patient.id == body.patient_id,
        Patient.is_active == True,
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    medications = db.query(Medication).filter(
        Medication.patient_id == body.patient_id,
    ).all()

    # RAG retrieval
    retrieved_chunks = retrieve_chunks(body.query, db, top_k=5)

    # LLM call
    ai_suggestion = generate_diagnosis_suggestion(
        patient=patient,
        medications=medications,
        retrieved_chunks=retrieved_chunks,
        doctor_query=body.query,
    )

    # Freeze citation metadata at this moment
    frozen_citations = [
        {
            "book_id": c["book_id"],
            "book_title": c["book_title"],
            "author": c.get("author"),
            "page_number": c["page_number"],
            "chunk_text": c["chunk_text"],
        }
        for c in retrieved_chunks
    ]

    record = Diagnosis(
        patient_id=body.patient_id,
        doctor_id=int(user["sub"]),
        query=body.query,
        ai_suggestion=ai_suggestion,
        citations=frozen_citations,
        decision="pending",
    )
    db.add(record)
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="doctor",
        action="diagnosis_queried",
        resource_type="patient",
        resource_id=body.patient_id,
        details=f"RAG query with {len(retrieved_chunks)} citation(s) retrieved",
    ))
    db.commit()
    db.refresh(record)

    return DiagnosisSuggestionResponse(
        diagnosis_id=record.id,
        patient_id=record.patient_id,
        query=record.query,
        ai_suggestion=record.ai_suggestion,
        citations=[CitationSchema(**c) for c in frozen_citations],
    )


@router.post("/{diagnosis_id}/decide", response_model=DiagnosisResponse)
def submit_decision(
    diagnosis_id: int,
    body: DiagnosisDecision,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    """Doctor marks the suggestion as accepted or modified, locking the final diagnosis."""
    _require_doctor(user)

    record = db.query(Diagnosis).filter(
        Diagnosis.id == diagnosis_id,
        Diagnosis.doctor_id == int(user["sub"]),
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    if record.decision != "pending":
        raise HTTPException(status_code=400, detail="Decision already submitted for this record")

    record.decision = body.decision
    record.final_diagnosis = body.final_diagnosis
    record.modification_note = body.modification_note
    record.decided_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="doctor",
        action=f"diagnosis_{body.decision}",
        resource_type="diagnosis",
        resource_id=diagnosis_id,
        details=f"Decision: {body.decision}" + (f" | Note: {body.modification_note}" if body.modification_note else ""),
    ))
    db.commit()
    db.refresh(record)
    return record


@router.get("/patient/{patient_id}", response_model=list[DiagnosisResponse])
def patient_diagnosis_history(
    patient_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    """Full diagnosis history — doctors/admins see all; patients see only their own confirmed diagnoses."""
    role = user.get("role")
    if role not in ("doctor", "super_admin", "patient"):
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "patient" and int(user["sub"]) != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="diagnosis_history_viewed",
        resource_type="patient",
        resource_id=patient_id,
    ))
    db.commit()

    return (
        db.query(Diagnosis)
        .filter(Diagnosis.patient_id == patient_id)
        .order_by(Diagnosis.suggested_at.desc())
        .all()
    )


@router.get("/{diagnosis_id}", response_model=DiagnosisResponse)
def get_diagnosis(
    diagnosis_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("doctor", "super_admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    record = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    return record
