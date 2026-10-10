from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.database import get_global_db, get_tenant_db
from core.dependencies import get_current_user
from core.security import create_access_token, verify_password
from models.global_models import CreatorAdmin, Hospital, StaffLookup
from models.tenant_models import SuperAdmin, Doctor, Patient
from schemas.auth import LoginRequest, MeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_global_db)):
    # 1. Try creator_admin first
    creator = db.query(CreatorAdmin).filter(
        CreatorAdmin.email == body.email,
        CreatorAdmin.is_active == True,
    ).first()

    if creator:
        if not verify_password(body.password, creator.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        creator.last_login = datetime.now(timezone.utc)
        db.commit()

        token = create_access_token({"sub": str(creator.id), "role": "creator_admin"})
        return TokenResponse(access_token=token, role="creator_admin", name=creator.name)

    # 2. Try hospital staff via lookup table
    lookup = db.query(StaffLookup).filter(
        StaffLookup.email == body.email,
        StaffLookup.is_active == True,
    ).first()

    if not lookup:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    hospital = db.query(Hospital).filter(Hospital.id == lookup.hospital_id).first()
    if not hospital or not hospital.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hospital account is inactive")

    # Verify password against the correct tenant DB
    tenant_db_gen = get_tenant_db(lookup.db_name)
    tenant_db: Session = next(tenant_db_gen)

    try:
        if lookup.role == "super_admin":
            from models.tenant_models import SuperAdmin as _SA
            staff = tenant_db.query(_SA).filter(
                _SA.email == body.email,
                _SA.is_active == True,
            ).first()
        elif lookup.role == "doctor":
            from models.tenant_models import Doctor
            staff = tenant_db.query(Doctor).filter(
                Doctor.email == body.email,
                Doctor.is_active == True,
            ).first()
        elif lookup.role == "patient":
            from models.tenant_models import Patient
            staff = tenant_db.query(Patient).filter(
                Patient.email == body.email,
                Patient.is_active == True,
            ).first()
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not staff or not verify_password(body.password, staff.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        staff.last_login = datetime.now(timezone.utc)
        tenant_db.commit()

        # Read values before session closes
        staff_id = staff.id
        staff_name = staff.name
    finally:
        tenant_db.close()

    token = create_access_token({
        "sub": str(staff_id),
        "role": lookup.role,
        "hospital_id": hospital.id,
        "hospital_name": hospital.name,
        "db_name": lookup.db_name,
    })
    return TokenResponse(
        access_token=token,
        role=lookup.role,
        name=staff_name,
        hospital_id=hospital.id,
        hospital_name=hospital.name,
    )


@router.get("/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user), db: Session = Depends(get_global_db)):
    role = user["role"]

    if role == "creator_admin":
        creator = db.query(CreatorAdmin).filter(CreatorAdmin.id == int(user["sub"])).first()
        if not creator:
            raise HTTPException(status_code=404, detail="User not found")
        return MeResponse(id=creator.id, name=creator.name, email=creator.email, role="creator_admin")

    # Hospital staff — fetch from tenant DB
    db_name = user.get("db_name")
    if not db_name:
        raise HTTPException(status_code=400, detail="Malformed token")

    tenant_db_gen = get_tenant_db(db_name)
    tenant_db: Session = next(tenant_db_gen)
    try:
        if role == "super_admin":
            staff = tenant_db.query(SuperAdmin).filter(SuperAdmin.id == int(user["sub"])).first()
        elif role == "doctor":
            staff = tenant_db.query(Doctor).filter(Doctor.id == int(user["sub"])).first()
        elif role == "patient":
            staff = tenant_db.query(Patient).filter(Patient.id == int(user["sub"])).first()
        else:
            raise HTTPException(status_code=400, detail="Role not supported yet")

        if not staff:
            raise HTTPException(status_code=404, detail="User not found")

        return MeResponse(
            id=staff.id,
            name=staff.name,
            email=staff.email,
            role=role,
            hospital_id=user.get("hospital_id"),
            hospital_name=user.get("hospital_name"),
        )
    finally:
        tenant_db.close()
