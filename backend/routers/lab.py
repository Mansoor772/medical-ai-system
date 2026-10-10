from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_global_db
from core.dependencies import get_current_user, get_tenant_session
from core.email import send_alert_notification
from models.global_models import Hospital
from models.tenant_models import AuditLog, LabResult, Patient
from schemas.lab import LabResultCreate, LabResultResponse, LabResultUpdate

router = APIRouter(prefix="/patients", tags=["Lab Results"])


def _require_doctor(user: dict) -> dict:
    if user.get("role") != "doctor":
        raise HTTPException(status_code=403, detail="Doctor access required")
    return user


@router.post("/{patient_id}/labs", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
def add_lab_result(
    patient_id: int,
    body: LabResultCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    _require_doctor(user)

    if not db.query(Patient).filter(Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")

    lab = LabResult(
        patient_id=patient_id,
        doctor_id=int(user["sub"]),
        test_name=body.test_name,
        test_date=body.test_date,
        result_value=body.result_value,
        unit=body.unit,
        reference_range=body.reference_range,
        is_abnormal=body.is_abnormal,
        notes=body.notes,
        alert_status="none",
    )
    db.add(lab)
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="doctor",
        action="lab_result_added",
        resource_type="patient",
        resource_id=patient_id,
        details=f"{body.test_name}: {body.result_value}" + (" [ABNORMAL]" if body.is_abnormal else ""),
    ))
    db.commit()
    db.refresh(lab)
    return lab


@router.get("/{patient_id}/labs", response_model=list[LabResultResponse])
def list_lab_results(
    patient_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("doctor", "super_admin", "patient"):
        raise HTTPException(status_code=403, detail="Access denied")

    # Patients can only see their own results
    if user.get("role") == "patient" and int(user["sub"]) != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return (
        db.query(LabResult)
        .filter(LabResult.patient_id == patient_id)
        .order_by(LabResult.test_date.desc())
        .all()
    )


@router.put("/{patient_id}/labs/{lab_id}", response_model=LabResultResponse)
def update_lab_result(
    patient_id: int,
    lab_id: int,
    body: LabResultUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    _require_doctor(user)

    lab = db.query(LabResult).filter(
        LabResult.id == lab_id,
        LabResult.patient_id == patient_id,
    ).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab result not found")
    if lab.alert_status in ("approved", "sent"):
        raise HTTPException(status_code=400, detail="Cannot edit a result after alert has been approved")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lab, field, value)

    db.commit()
    db.refresh(lab)
    return lab


@router.post("/{patient_id}/labs/{lab_id}/flag-alert", response_model=LabResultResponse)
def flag_for_alert(
    patient_id: int,
    lab_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    """Doctor flags a result as needing an alert — moves to pending approval."""
    _require_doctor(user)

    lab = db.query(LabResult).filter(
        LabResult.id == lab_id,
        LabResult.patient_id == patient_id,
    ).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab result not found")
    if lab.alert_status != "none":
        raise HTTPException(status_code=400, detail=f"Alert already in status: {lab.alert_status}")

    lab.alert_status = "pending"
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="doctor",
        action="lab_alert_flagged",
        resource_type="patient",
        resource_id=patient_id,
        details=f"Lab result {lab_id} ({lab.test_name}) flagged for alert",
    ))
    db.commit()
    db.refresh(lab)
    return lab


@router.post("/{patient_id}/labs/{lab_id}/approve-alert", response_model=LabResultResponse)
def approve_alert(
    patient_id: int,
    lab_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
    global_db: Session = Depends(get_global_db),
):
    """Doctor approves the alert → sends email notification to hospital Super Admin."""
    _require_doctor(user)

    lab = db.query(LabResult).filter(
        LabResult.id == lab_id,
        LabResult.patient_id == patient_id,
    ).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab result not found")
    if lab.alert_status != "pending":
        raise HTTPException(status_code=400, detail="Lab result is not pending approval")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    # Get hospital contact email from global DB
    hospital = global_db.query(Hospital).filter(
        Hospital.id == user["hospital_id"]
    ).first()
    recipient_email = hospital.contact_email if hospital else None

    lab.alert_approved_by = int(user["sub"])
    lab.alert_approved_at = datetime.now(timezone.utc)

    email_sent = False
    if recipient_email:
        email_sent = send_alert_notification(
            to=recipient_email,
            hospital_name=user.get("hospital_name", ""),
            patient_name=patient.name if patient else f"Patient #{patient_id}",
            test_name=lab.test_name,
            result_value=lab.result_value,
            unit=lab.unit,
            reference_range=lab.reference_range,
            doctor_notes=lab.notes,
        )

    lab.alert_status = "sent" if email_sent else "approved"
    lab.alert_sent_at = datetime.now(timezone.utc) if email_sent else None

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="doctor",
        action="lab_alert_approved",
        resource_type="patient",
        resource_id=patient_id,
        details=f"Alert approved for {lab.test_name}. Email sent: {email_sent}",
    ))
    db.commit()
    db.refresh(lab)
    return lab
