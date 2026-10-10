from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies import get_tenant_session, require_super_admin
from core.security import hash_password, verify_password
from models.tenant_models import AuditLog, SuperAdmin
from schemas.admin import PasswordChange, SuperAdminProfile, SuperAdminUpdate

router = APIRouter(prefix="/admin", tags=["Super Admin"])


@router.get("/profile", response_model=SuperAdminProfile)
def get_profile(
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    admin = db.query(SuperAdmin).filter(SuperAdmin.id == int(user["sub"])).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")
    return admin


@router.put("/profile", response_model=SuperAdminProfile)
def update_profile(
    body: SuperAdminUpdate,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    admin = db.query(SuperAdmin).filter(SuperAdmin.id == int(user["sub"])).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(admin, field, value)

    db.add(AuditLog(
        actor_id=admin.id,
        actor_role="super_admin",
        action="profile_updated",
        resource_type="super_admin",
        resource_id=admin.id,
    ))
    db.commit()
    db.refresh(admin)
    return admin


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    body: PasswordChange,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    admin = db.query(SuperAdmin).filter(SuperAdmin.id == int(user["sub"])).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not verify_password(body.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    admin.password_hash = hash_password(body.new_password)
    db.add(AuditLog(
        actor_id=admin.id,
        actor_role="super_admin",
        action="password_changed",
        resource_type="super_admin",
        resource_id=admin.id,
    ))
    db.commit()
    return {"message": "Password changed successfully"}


@router.get("/audit-log")
def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_super_admin),
    db: Session = Depends(get_tenant_session),
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": log.id,
            "actor_id": log.actor_id,
            "actor_role": log.actor_role,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at,
        }
        for log in logs
    ]
