from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-members"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/members", response_model=schemas.AdminMemberListOut)
def list_admin_members(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    return crud.admin_list_members(db, search=search, page=page, page_size=page_size)


@router.put("/members/{member_id}", response_model=schemas.AdminMemberOut)
def update_member_status(
    member_id: int,
    payload: schemas.MemberStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    if member_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")
    member = db.get(models.User, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot suspend an admin account")

    member.is_active = payload.is_active
    db.commit()
    db.refresh(member)

    fav_count = db.query(models.Favorite).filter_by(user_id=member.id).count()
    return schemas.AdminMemberOut(
        id=member.id, name=member.name, email=member.email, role=member.role,
        isActive=member.is_active, createdAt=member.created_at, favoriteCount=fav_count,
    )


@router.get("/stats", response_model=schemas.AdminStatsOut)
def get_admin_stats(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_admin(user)
    return crud.admin_stats(db)
