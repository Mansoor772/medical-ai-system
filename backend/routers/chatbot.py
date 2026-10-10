from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_tenant_session
from core.llm import answer_patient_query
from models.tenant_models import AuditLog, Diagnosis, LabResult, Medication, Patient

router = APIRouter(prefix="/chatbot", tags=["Patient Chatbot"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=ChatResponse)
def patient_ask(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    """
    Patient-only endpoint. Answers questions strictly from doctor-entered records.
    Diagnostic or medical advice questions are redirected to consult the doctor.
    """
    if user.get("role") != "patient":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for patients only. Doctors use the diagnosis module.",
        )

    patient_id = int(user["sub"])
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.is_active == True).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    lab_results = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    diagnoses = (
        db.query(Diagnosis)
        .filter(Diagnosis.patient_id == patient_id, Diagnosis.decision.in_(["accepted", "modified"]))
        .order_by(Diagnosis.decided_at.desc())
        .all()
    )

    answer = answer_patient_query(
        patient=patient,
        medications=medications,
        lab_results=lab_results,
        diagnoses=diagnoses,
        question=body.question,
    )

    db.add(AuditLog(
        actor_id=patient_id,
        actor_role="patient",
        action="chatbot_query",
        resource_type="patient",
        resource_id=patient_id,
        details=f"Q: {body.question[:100]}",
    ))
    db.commit()

    return ChatResponse(answer=answer)
