from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_global_db, get_tenant_db
from core.dependencies import get_current_user, get_tenant_session, require_super_admin
from core.security import hash_password
from models.global_models import StaffLookup
from models.tenant_models import AuditLog, Doctor
from schemas.doctor import DoctorCreate, DoctorListItem, DoctorResponse, DoctorUpdate

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def register_doctor(
    body: DoctorCreate,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
    global_db: Session = Depends(get_global_db),
):
    # Check duplicate email within this hospital
    if db.query(Doctor).filter(Doctor.email == body.email).first():
        raise HTTPException(status_code=400, detail="A doctor with this email already exists")

    # Check global staff_lookup for cross-hospital email conflict
    if global_db.query(StaffLookup).filter(StaffLookup.email == body.email).first():
        raise HTTPException(status_code=400, detail="This email is already registered in the system")

    doctor = Doctor(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        phone=body.phone,
        license_number=body.license_number,
        specialization=body.specialization,
        qualification=body.qualification,
        registered_by=int(user["sub"]),
    )
    db.add(doctor)
    db.flush()

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="doctor_registered",
        resource_type="doctor",
        resource_id=doctor.id,
        details=f"Doctor '{body.name}' ({body.specialization}) registered",
    ))
    db.commit()

    # Add to global staff_lookup so doctor can log in
    global_db.add(StaffLookup(
        email=body.email,
        role="doctor",
        hospital_id=user["hospital_id"],
        db_name=user["db_name"],
    ))
    global_db.commit()

    db.refresh(doctor)
    return doctor


@router.get("/", response_model=list[DoctorListItem])
def list_doctors(
    active_only: bool = True,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("super_admin", "doctor"):
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Doctor)
    if active_only:
        query = query.filter(Doctor.is_active == True)
    return query.order_by(Doctor.name).all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_tenant_session),
):
    if user.get("role") not in ("super_admin", "doctor"):
        raise HTTPException(status_code=403, detail="Access denied")

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    body: DoctorUpdate,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doctor, field, value)

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="doctor_updated",
        resource_type="doctor",
        resource_id=doctor_id,
    ))
    db.commit()
    db.refresh(doctor)
    return doctor


@router.post("/{doctor_id}/deactivate")
def deactivate_doctor(
    doctor_id: int,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
    global_db: Session = Depends(get_global_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if not doctor.is_active:
        raise HTTPException(status_code=400, detail="Doctor is already inactive")

    doctor.is_active = False
    global_db.query(StaffLookup).filter(StaffLookup.email == doctor.email).update({"is_active": False})

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="doctor_deactivated",
        resource_type="doctor",
        resource_id=doctor_id,
    ))
    db.commit()
    global_db.commit()
    return {"message": f"Doctor '{doctor.name}' has been deactivated"}


@router.post("/{doctor_id}/reactivate")
def reactivate_doctor(
    doctor_id: int,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
    global_db: Session = Depends(get_global_db),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if doctor.is_active:
        raise HTTPException(status_code=400, detail="Doctor is already active")

    doctor.is_active = True
    global_db.query(StaffLookup).filter(StaffLookup.email == doctor.email).update({"is_active": True})

    db.add(AuditLog(
        actor_id=int(user["sub"]),
        actor_role="super_admin",
        action="doctor_reactivated",
        resource_type="doctor",
        resource_id=doctor_id,
    ))
    db.commit()
    global_db.commit()
    return {"message": f"Doctor '{doctor.name}' has been reactivated"}
