from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_global_db
from core.dependencies import get_current_user, get_tenant_session, require_creator_admin, require_super_admin
from models.global_models import Hospital
from models.tenant_models import AuditLog, Diagnosis, Doctor, LabResult, Medication, Patient, PatientConsent, SuperAdmin

router = APIRouter(prefix="/compliance", tags=["Compliance (PDPA)"])

_REDACTED = "[REDACTED - PDPA Request]"


# ── Patient data export (PDPA right to access) ────────────────────────────────

@router.get("/patients/{patient_id}/export")
def export_patient_data(
    patient_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    """Returns a complete JSON export of a patient's data (PDPA right to access)."""
    if user.get("role") not in ("super_admin", "doctor"):
        raise HTTPException(status_code=403, detail="Access denied")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient_id).all()
    consent = db.query(PatientConsent).filter(PatientConsent.patient_id == patient_id).first()

    export = {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "export_type": "PDPA Right to Access",
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "date_of_birth": str(patient.date_of_birth),
            "gender": patient.gender,
            "blood_group": patient.blood_group,
            "cnic": patient.cnic,
            "phone": patient.phone,
            "email": patient.email,
            "address": patient.address,
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_phone": patient.emergency_contact_phone,
            "emergency_contact_relation": patient.emergency_contact_relation,
            "past_diseases": patient.past_diseases,
            "past_surgeries": patient.past_surgeries,
            "allergies": patient.allergies,
            "family_history": patient.family_history,
            "registered_at": patient.created_at.isoformat(),
        },
        "consent": {
            "consented_at": consent.consented_at.isoformat() if consent else None,
            "consent_version": consent.consent_version if consent else None,
            "consent_text": consent.consent_text if consent else None,
        },
        "medications": [
            {
                "medicine_name": m.medicine_name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "route": m.route,
                "start_date": str(m.start_date),
                "end_date": str(m.end_date) if m.end_date else None,
                "is_current": m.is_current,
                "notes": m.notes,
            }
            for m in medications
        ],
        "lab_results": [
            {
                "test_name": l.test_name,
                "test_date": str(l.test_date),
                "result_value": l.result_value,
                "unit": l.unit,
                "reference_range": l.reference_range,
                "is_abnormal": l.is_abnormal,
                "notes": l.notes,
            }
            for l in labs
        ],
        "diagnoses": [
            {
                "query": d.query,
                "final_diagnosis": d.final_diagnosis,
                "decision": d.decision,
                "suggested_at": d.suggested_at.isoformat(),
                "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            }
            for d in diagnoses if d.decision in ("accepted", "modified")
        ],
    }

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role=user["role"],
        action="patient_data_exported",
        resource_type="patient",
        resource_id=patient_id,
        details="PDPA right-to-access export generated",
    ))
    db.commit()

    return JSONResponse(content=export, headers={
        "Content-Disposition": f'attachment; filename="patient_{patient_id}_export.json"'
    })


# ── Patient anonymization (PDPA right to deletion) ────────────────────────────

@router.post("/patients/{patient_id}/anonymize")
def anonymize_patient(
    patient_id: int,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    """
    Replaces patient PII with REDACTED markers (PDPA right to deletion).
    Medical record structure is preserved for clinical/legal retention requirements.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.name == _REDACTED:
        raise HTTPException(status_code=400, detail="Patient data is already anonymized")

    patient.name = _REDACTED
    patient.cnic = _REDACTED
    patient.phone = _REDACTED
    patient.email = None
    patient.password_hash = None
    patient.address = _REDACTED
    patient.emergency_contact_name = _REDACTED
    patient.emergency_contact_phone = _REDACTED
    patient.is_active = False

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="patient_anonymized",
        resource_type="patient",
        resource_id=patient_id,
        details="Patient PII anonymized per PDPA right-to-deletion request. Medical records retained.",
    ))
    db.commit()
    return {"message": "Patient personal data has been anonymized. Medical records are retained for legal compliance."}


# ── Hospital data export (offboarding) ────────────────────────────────────────

@router.get("/hospitals/{hospital_id}/export")
def export_hospital_data(
    hospital_id: int,
    user: dict = Depends(require_creator_admin),
    global_db: Session = Depends(get_global_db),
):
    """
    Exports all data for a hospital as JSON.
    Creator Admin uses this during offboarding to hand data back to the clinic.
    """
    hospital = global_db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    from core.database import get_tenant_db
    tenant_db_gen = get_tenant_db(hospital.db_name)
    tenant_db: Session = next(tenant_db_gen)

    try:
        patients = tenant_db.query(Patient).all()
        doctors = tenant_db.query(Doctor).all()
        super_admins = tenant_db.query(SuperAdmin).all()
        medications = tenant_db.query(Medication).all()
        labs = tenant_db.query(LabResult).all()
        diagnoses = tenant_db.query(Diagnosis).all()

        export = {
            "export_generated_at": datetime.now(timezone.utc).isoformat(),
            "hospital": {
                "id": hospital.id,
                "name": hospital.name,
                "city": hospital.city,
                "contact_email": hospital.contact_email,
            },
            "summary": {
                "total_patients": len(patients),
                "total_doctors": len(doctors),
                "total_diagnoses": len(diagnoses),
                "total_lab_results": len(labs),
            },
            "patients": [
                {
                    "id": p.id, "name": p.name, "date_of_birth": str(p.date_of_birth),
                    "gender": p.gender, "cnic": p.cnic, "phone": p.phone,
                    "email": p.email, "blood_group": p.blood_group,
                    "past_diseases": p.past_diseases, "allergies": p.allergies,
                }
                for p in patients
            ],
            "doctors": [
                {
                    "id": d.id, "name": d.name, "email": d.email,
                    "license_number": d.license_number, "specialization": d.specialization,
                }
                for d in doctors
            ],
            "medications": [
                {
                    "patient_id": m.patient_id, "medicine_name": m.medicine_name,
                    "dosage": m.dosage, "frequency": m.frequency,
                    "start_date": str(m.start_date), "is_current": m.is_current,
                }
                for m in medications
            ],
            "lab_results": [
                {
                    "patient_id": l.patient_id, "test_name": l.test_name,
                    "test_date": str(l.test_date), "result_value": l.result_value,
                    "unit": l.unit, "is_abnormal": l.is_abnormal,
                }
                for l in labs
            ],
            "diagnoses": [
                {
                    "patient_id": d.patient_id, "doctor_id": d.doctor_id,
                    "final_diagnosis": d.final_diagnosis, "decision": d.decision,
                    "suggested_at": d.suggested_at.isoformat(),
                }
                for d in diagnoses if d.decision in ("accepted", "modified")
            ],
        }
    finally:
        tenant_db.close()

    return JSONResponse(content=export, headers={
        "Content-Disposition": f'attachment; filename="{hospital.name.replace(" ", "_")}_export.json"'
    })
