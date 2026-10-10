from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import (
    create_hospital_database,
    generate_db_name,
    get_global_db,
    get_tenant_db,
    provision_tenant_schema,
)
from core.dependencies import require_creator_admin
from core.security import hash_password
from models.global_models import Hospital, StaffLookup
from models.tenant_models import AuditLog, SuperAdmin
from schemas.hospital import (
    HospitalCreate,
    HospitalListItem,
    HospitalResponse,
    HospitalUpdate,
)

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])


@router.post("/", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
def create_hospital(
    body: HospitalCreate,
    db: Session = Depends(get_global_db),
    user: dict = Depends(require_creator_admin),
):
    # Check duplicate name + city
    existing = db.query(Hospital).filter(
        Hospital.name == body.name,
        Hospital.city == body.city,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A hospital with this name already exists in this city")

    # Check email uniqueness in staff_lookup
    email_taken = db.query(StaffLookup).filter(StaffLookup.email == body.super_admin.email).first()
    if email_taken:
        raise HTTPException(status_code=400, detail="Super admin email is already registered")

    # Generate DB name and create the PostgreSQL database
    db_name = generate_db_name(body.name)
    create_hospital_database(db_name)
    provision_tenant_schema(db_name)

    # Insert hospital record in global DB
    hospital = Hospital(
        name=body.name,
        city=body.city,
        address=body.address,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        db_name=db_name,
    )
    db.add(hospital)
    db.flush()  # get hospital.id before commit

    # Create super admin in tenant DB
    tenant_db_gen = get_tenant_db(db_name)
    tenant_db: Session = next(tenant_db_gen)
    try:
        admin = SuperAdmin(
            name=body.super_admin.name,
            email=body.super_admin.email,
            password_hash=hash_password(body.super_admin.password),
            phone=body.super_admin.phone,
        )
        tenant_db.add(admin)
        tenant_db.flush()

        tenant_db.add(AuditLog(
            actor_id=int(user["sub"]),
            actor_role="creator_admin",
            action="hospital_provisioned",
            resource_type="hospital",
            details=f"Hospital '{body.name}' created with DB '{db_name}'",
        ))
        tenant_db.commit()
    finally:
        tenant_db.close()

    # Register super admin in global staff_lookup
    db.add(StaffLookup(
        email=body.super_admin.email,
        role="super_admin",
        hospital_id=hospital.id,
        db_name=db_name,
    ))
    db.commit()
    db.refresh(hospital)
    return hospital


@router.get("/", response_model=list[HospitalListItem])
def list_hospitals(
    db: Session = Depends(get_global_db),
    _: dict = Depends(require_creator_admin),
):
    return db.query(Hospital).order_by(Hospital.created_at.desc()).all()


@router.get("/{hospital_id}", response_model=HospitalResponse)
def get_hospital(
    hospital_id: int,
    db: Session = Depends(get_global_db),
    _: dict = Depends(require_creator_admin),
):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hospital


@router.put("/{hospital_id}", response_model=HospitalResponse)
def update_hospital(
    hospital_id: int,
    body: HospitalUpdate,
    db: Session = Depends(get_global_db),
    _: dict = Depends(require_creator_admin),
):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(hospital, field, value)

    db.commit()
    db.refresh(hospital)
    return hospital


@router.post("/{hospital_id}/deactivate", status_code=status.HTTP_200_OK)
def deactivate_hospital(
    hospital_id: int,
    db: Session = Depends(get_global_db),
    _: dict = Depends(require_creator_admin),
):
    """Soft-deactivate a hospital. Does not delete data."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if not hospital.is_active:
        raise HTTPException(status_code=400, detail="Hospital is already inactive")

    hospital.is_active = False
    hospital.deactivated_at = datetime.now(timezone.utc)

    # Also deactivate all staff lookups for this hospital
    db.query(StaffLookup).filter(StaffLookup.hospital_id == hospital_id).update(
        {"is_active": False}
    )
    db.commit()
    return {"message": f"Hospital '{hospital.name}' has been deactivated"}


@router.post("/{hospital_id}/reactivate", status_code=status.HTTP_200_OK)
def reactivate_hospital(
    hospital_id: int,
    db: Session = Depends(get_global_db),
    _: dict = Depends(require_creator_admin),
):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if hospital.is_active:
        raise HTTPException(status_code=400, detail="Hospital is already active")

    hospital.is_active = True
    hospital.deactivated_at = None

    db.query(StaffLookup).filter(StaffLookup.hospital_id == hospital_id).update(
        {"is_active": True}
    )
    db.commit()
    return {"message": f"Hospital '{hospital.name}' has been reactivated"}
