from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/accommodations", response_model=schemas.AdminAccommodationListOut)
def list_admin_accommodations(
    status: str | None = Query(default=None, description="draft|pending_review|published|closed"),
    district: str | None = Query(default=None, description="districts.name, exact match"),
    type: str | None = Query(default=None, description="accommodation_types.code"),
    search: str | None = Query(default=None, description="name contains this text"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """The admin accommodations table (scope 4.1) — every status, not just
    'published', with a name search and newest-edited-first ordering."""
    _require_admin(user)
    items, total = crud.admin_list_accommodations(
        db, status=status, district_name=district, type_code=type, search=search, page=page, page_size=page_size
    )
    return schemas.AdminAccommodationListOut(
        items=[crud.to_admin_accommodation_out(a) for a in items],
        total=total,
        page=page,
        pageSize=page_size,
    )


@router.get("/accommodations/summary", response_model=schemas.AdminSummaryOut)
def get_admin_accommodations_summary(
    status: str | None = Query(default=None, description="draft|pending_review|published|closed"),
    search: str | None = Query(default=None, description="name contains this text"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """How many accommodations exist per อำเภอ x ประเภท — respects the same
    status/search filters as the table above it, for a quick data-completeness
    check (e.g. 'อำเภอเมือง has 0 โฮมสเตย์')."""
    _require_admin(user)
    return crud.admin_district_type_counts(db, status=status, search=search)
