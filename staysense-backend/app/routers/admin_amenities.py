from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-amenities"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _validate_category(category: str | None) -> None:
    if category is not None and category not in schemas.VALID_AMENITY_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {sorted(schemas.VALID_AMENITY_CATEGORIES)}")


@router.get("/amenities", response_model=list[schemas.AdminAmenityOut])
def list_admin_amenities(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    _require_admin(user)
    return crud.admin_list_amenities(db)


@router.get("/amenity-categories")
def list_amenity_categories(user: models.User = Depends(get_current_user)):
    _require_admin(user)
    return schemas.AMENITY_CATEGORIES


@router.post("/amenities", response_model=schemas.AdminAmenityOut, status_code=201)
def create_admin_amenity(
    payload: schemas.AmenityCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    _validate_category(payload.category)
    if db.query(models.Amenity).filter_by(code=payload.code).first():
        raise HTTPException(status_code=400, detail=f"Amenity code '{payload.code}' already exists")

    amenity = models.Amenity(
        code=payload.code,
        label_th=payload.label_th,
        category=payload.category,
        icon_key=payload.icon_key,
    )
    db.add(amenity)
    db.commit()
    db.refresh(amenity)
    return schemas.AdminAmenityOut(id=amenity.id, key=amenity.code, label=amenity.label_th, category=amenity.category, accommodationCount=0)


@router.put("/amenities/{amenity_id}", response_model=schemas.AdminAmenityOut)
def update_admin_amenity(
    amenity_id: int,
    payload: schemas.AmenityUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    _validate_category(payload.category)
    amenity = db.get(models.Amenity, amenity_id)
    if not amenity:
        raise HTTPException(status_code=404, detail="Amenity not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(amenity, field, value)
    db.commit()
    db.refresh(amenity)

    count = (
        db.query(models.AccommodationAmenity)
        .filter_by(amenity_id=amenity.id)
        .count()
    )
    return schemas.AdminAmenityOut(id=amenity.id, key=amenity.code, label=amenity.label_th, category=amenity.category, accommodationCount=count)


@router.delete("/amenities/{amenity_id}", status_code=204)
def delete_admin_amenity(
    amenity_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    amenity = db.get(models.Amenity, amenity_id)
    if not amenity:
        raise HTTPException(status_code=404, detail="Amenity not found")
    db.delete(amenity)
    db.commit()
