"""
資格情報管理 API
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.encryption import EncryptionManager
from app.models.models import EigaComCredentials

router = APIRouter()


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}" if local else f"***@{domain}"
    return f"{local[:2]}***@{domain}"


class CredentialView(BaseModel):
    has_credentials: bool
    email_masked: Optional[str] = None
    is_active: Optional[bool] = None
    last_sync: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CredentialUpsertRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = True


@router.get("/eiga", response_model=CredentialView)
async def get_credentials(db: Session = Depends(get_db)):
    """有効な映画.com資格情報のメタ情報を取得（平文は返さない）。"""
    cred = (
        db.query(EigaComCredentials)
        .filter(EigaComCredentials.is_active == True)
        .order_by(EigaComCredentials.updated_at.desc())
        .first()
    )
    if not cred:
        return CredentialView(has_credentials=False)

    return CredentialView(
        has_credentials=True,
        email_masked=_mask_email(cred.email),
        is_active=cred.is_active,
        last_sync=cred.last_sync,
        updated_at=cred.updated_at,
    )


@router.put("/eiga", response_model=CredentialView)
async def put_credentials(payload: CredentialUpsertRequest, db: Session = Depends(get_db)):
    """
    資格情報の保存/更新/有効化。
    - email+password: 保存または更新
    - email + is_active: 有効化/無効化のみ更新
    """
    if not payload.email:
        raise HTTPException(status_code=422, detail="email is required")

    cred = db.query(EigaComCredentials).filter(EigaComCredentials.email == payload.email).first()

    if payload.password:
        encrypted = EncryptionManager.encrypt(payload.password)
        if cred:
            cred.password_encrypted = encrypted
        else:
            cred = EigaComCredentials(email=payload.email, password_encrypted=encrypted)
            db.add(cred)
    elif not cred:
        raise HTTPException(status_code=404, detail="credentials not found")

    if payload.is_active is not None:
        if payload.is_active:
            db.query(EigaComCredentials).filter(EigaComCredentials.email != payload.email).update(
                {EigaComCredentials.is_active: False},
                synchronize_session=False,
            )
        cred.is_active = payload.is_active

    db.commit()
    db.refresh(cred)

    return CredentialView(
        has_credentials=cred.is_active,
        email_masked=_mask_email(cred.email),
        is_active=cred.is_active,
        last_sync=cred.last_sync,
        updated_at=cred.updated_at,
    )


@router.delete("/eiga")
async def delete_credentials(db: Session = Depends(get_db)):
    """保存済み資格情報を削除する。"""
    deleted = db.query(EigaComCredentials).delete(synchronize_session=False)
    db.commit()
    return {"success": True, "deleted": deleted}
