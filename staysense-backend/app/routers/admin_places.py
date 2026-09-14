from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-places"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _validate_category(category: str | None) -> None:
    if category is not None and category not in schemas.VALID_PLACE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {sorted(schemas.VALID_PLACE_CATEGORIES)}")


def _resolve_district_id(db: Session, district_name: str | None) -> int | None:
    if not district_name:
        return None
    district = db.query(models.District).filter_by(name=district_name).first()
    if not district:
        raise HTTPException(status_code=400, detail=f"Unknown district_name '{district_name}'")
    return district.id


@router.get("/places", response_model=list[schemas.AdminPlaceOut])
def list_admin_places(
    district: str | None = None,
    category: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    return crud.admin_list_places(db, district_name=district, category=category, search=search)


@router.get("/place-categories")
def list_place_categories(user: models.User = Depends(get_current_user)):
    _require_admin(user)
    return schemas.PLACE_CATEGORIES


@router.post("/places", response_model=schemas.AdminPlaceOut, status_code=201)
def create_admin_place(
    payload: schemas.PlaceCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    _validate_category(payload.category)
    district_id = _resolve_district_id(db, payload.district_name)

    place = models.Place(
        name=payload.name,
        category=payload.category,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        is_popular=payload.is_popular,
        source_note=payload.source_note,
        district_id=district_id,
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return crud.to_admin_place_out(place)


@router.put("/places/{place_id}", response_model=schemas.AdminPlaceOut)
def update_admin_place(
    place_id: int,
    payload: schemas.PlaceUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    _validate_category(payload.category)
    place = db.get(models.Place, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    data = payload.model_dump(exclude_unset=True)
    district_name = data.pop("district_name", None)
    if "district_name" in payload.model_fields_set:
        place.district_id = _resolve_district_id(db, district_name)
    for field, value in data.items():
        setattr(place, field, value)

    db.commit()
    db.refresh(place)
    return crud.to_admin_place_out(place)


@router.delete("/places/{place_id}", status_code=204)
def delete_admin_place(
    place_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    place = db.get(models.Place, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    db.delete(place)
    db.commit()
