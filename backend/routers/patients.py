from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_global_db
from core.dependencies import get_current_user, get_tenant_session, require_super_admin
from core.security import hash_password
from models.global_models import StaffLookup
from models.tenant_models import AuditLog, Medication, Patient, PatientConsent
from schemas.patient import (
    MedicationCreate,
    MedicationResponse,
    MedicationUpdate,
    PatientCreate,
    PatientDemographicsUpdate,
    PatientListItem,
    PatientMedicalHistoryUpdate,
    PatientResponse,
)

router = APIRouter(prefix="/patients", tags=["Patients"])

CONSENT_TEXT = (
    "I consent to the collection, storage, and processing of my personal health information "
    "by this clinic for medical treatment purposes, in accordance with Pakistan's Personal "
    "Data Protection Act (PDPA). My data will only be accessed by authorized medical staff "
    "at this clinic."
)


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(
    body: PatientCreate,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
    global_db: Session = Depends(get_global_db),
):
    if body.email and global_db.query(StaffLookup).filter(StaffLookup.email == body.email).first():
        raise HTTPException(status_code=400, detail="This email is already registered in the system")

    patient = Patient(
        name=body.name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        blood_group=body.blood_group,
        cnic=body.cnic,
        phone=body.phone,
        email=body.email,
        password_hash=hash_password(body.password) if body.password else None,
        address=body.address,
        emergency_contact_name=body.emergency_contact_name,
        emergency_contact_phone=body.emergency_contact_phone,
        emergency_contact_relation=body.emergency_contact_relation,
        past_diseases=body.past_diseases,
        past_surgeries=body.past_surgeries,
        allergies=body.allergies,
        family_history=body.family_history,
        registered_by=int(user["sub"]),
    )
    db.add(patient)
    db.flush()

    # PDPA consent record
    db.add(PatientConsent(
        patient_id=patient.id,
        consent_text=CONSENT_TEXT,
        consent_version="1.0",
        registered_by=int(user["sub"]),
    ))

    # Initial medications if provided
    if body.medications:
        for med in body.medications:
            db.add(Medication(
                patient_id=patient.id,
                medicine_name=med.medicine_name,
                dosage=med.dosage,
                frequency=med.frequency,
                route=med.route,
                start_date=med.start_date,
                end_date=med.end_date,
                notes=med.notes,
                is_current=True,
            ))

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="patient_registered",
        resource_type="patient",
        resource_id=patient.id,
        details=f"Patient '{body.name}' registered with PDPA consent",
    ))
    db.commit()

    # Add patient to global staff_lookup so they can log in (only if email + password provided)
    if body.email and body.password:
        global_db.add(StaffLookup(
            email=body.email,
            role="patient",
            hospital_id=user["hospital_id"],
            db_name=user["db_name"],
        ))
        global_db.commit()

    db.refresh(patient)
    return patient


@router.get("/", response_model=list[PatientListItem])
def list_patients(
    active_only: bool = True,
    search: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("super_admin", "doctor"):
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Patient)
    if active_only:
        query = query.filter(Patient.is_active == True)
    if search:
        query = query.filter(
            Patient.name.ilike(f"%{search}%") | Patient.cnic.ilike(f"%{search}%")
        )
    return query.order_by(Patient.name).all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    role = user.get("role")
    if role not in ("super_admin", "doctor", "patient"):
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "patient" and int(user["sub"]) != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="patient_viewed",
        resource_type="patient",
        resource_id=patient_id,
    ))
    db.commit()

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}/demographics", response_model=PatientResponse)
def update_demographics(
    patient_id: int,
    body: PatientDemographicsUpdate,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(patient, field, value)

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="patient_demographics_updated",
        resource_type="patient",
        resource_id=patient_id,
    ))
    db.commit()
    db.refresh(patient)
    return patient


@router.put("/{patient_id}/medical-history", response_model=PatientResponse)
def update_medical_history(
    patient_id: int,
    body: PatientMedicalHistoryUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("doctor", "super_admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(patient, field, value)

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="patient_medical_history_updated",
        resource_type="patient",
        resource_id=patient_id,
    ))
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/{patient_id}/deactivate")
def deactivate_patient(
    patient_id: int,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.is_active = False
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="patient_deactivated",
        resource_type="patient",
        resource_id=patient_id,
    ))
    db.commit()
    return {"message": f"Patient '{patient.name}' has been deactivated"}


# ── Medications ────────────────────────────────────────────────────────────────

@router.get("/{patient_id}/medications", response_model=list[MedicationResponse])
def list_medications(
    patient_id: int,
    current_only: bool = False,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    role = user.get("role")
    if role not in ("super_admin", "doctor", "patient"):
        raise HTTPException(status_code=403, detail="Access denied")
    if role == "patient" and int(user["sub"]) != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Medication).filter(Medication.patient_id == patient_id)
    if current_only:
        query = query.filter(Medication.is_current == True)
    return query.order_by(Medication.start_date.desc()).all()


@router.post("/{patient_id}/medications", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
def add_medication(
    patient_id: int,
    body: MedicationCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("super_admin", "doctor"):
        raise HTTPException(status_code=403, detail="Access denied")

    if not db.query(Patient).filter(Patient.id == patient_id).first():
        raise HTTPException(status_code=404, detail="Patient not found")

    prescribed_by = int(user["sub"]) if user["role"] == "doctor" else None
    med = Medication(
        patient_id=patient_id,
        medicine_name=body.medicine_name,
        dosage=body.dosage,
        frequency=body.frequency,
        route=body.route,
        start_date=body.start_date,
        end_date=body.end_date,
        prescribed_by=prescribed_by,
        notes=body.notes,
        is_current=True,
    )
    db.add(med)
    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="medication_added",
        resource_type="patient",
        resource_id=patient_id,
        details=f"Added {body.medicine_name} {body.dosage}",
    ))
    db.commit()
    db.refresh(med)
    return med


@router.put("/{patient_id}/medications/{med_id}", response_model=MedicationResponse)
def update_medication(
    patient_id: int,
    med_id: int,
    body: MedicationUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("super_admin", "doctor"):
        raise HTTPException(status_code=403, detail="Access denied")

    med = db.query(Medication).filter(
        Medication.id == med_id,
        Medication.patient_id == patient_id,
    ).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(med, field, value)

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="medication_updated",
        resource_type="patient",
        resource_id=patient_id,
        details=f"Updated medication id={med_id}",
    ))
    db.commit()
    db.refresh(med)
    return med
