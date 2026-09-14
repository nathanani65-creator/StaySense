from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user, get_current_user_optional
from ..database import get_db
from ..semantic import index as search_index

router = APIRouter(prefix="/api/accommodations", tags=["accommodations"])

VALID_STATUSES = {"draft", "pending_review", "published", "closed"}


@router.get("", response_model=schemas.AccommodationListOut)
def list_accommodations(
    type: str | None = Query(default=None, description="accommodation_types.code, e.g. 'hotel'"),
    district: list[str] = Query(default=[], description="district name(s), repeatable"),
    price_min: float | None = None,
    price_max: float | None = None,
    rating_min: float | None = None,
    amenities: list[str] = Query(default=[], description="amenities.code, repeatable; AND semantics"),
    distance_max_km: float | None = None,
    sort: str | None = Query(default="recommended"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=6, ge=1, le=50),
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user_optional),
):
    items, total = crud.list_accommodations(
        db,
        type_code=type,
        district_names=district or None,
        price_min=price_min,
        price_max=price_max,
        rating_min=rating_min,
        amenity_codes=amenities or None,
        distance_max_km=distance_max_km,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    fav_ids = crud.user_favorite_ids(db, user)
    return schemas.AccommodationListOut(
        items=crud.apply_fav_flags([crud.to_accommodation_out(a) for a in items], fav_ids),
        total=total,
        page=page,
        pageSize=page_size,
    )


@router.get("/{accommodation_id}", response_model=schemas.AccommodationDetailOut)
def get_accommodation(
    accommodation_id: int,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user_optional),
):
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    # an admin previewing/editing a draft or hidden room type sees everything;
    # the public page never does (see crud.to_accommodation_detail_out)
    is_admin = bool(user and user.role == "admin")
    detail = crud.to_accommodation_detail_out(acc, include_hidden_rooms=is_admin)
    return crud.apply_fav_flags(detail, crud.user_favorite_ids(db, user))


@router.get("/{accommodation_id}/nearby", response_model=schemas.NearbyOut)
def get_nearby_places(accommodation_id: int, db: Session = Depends(get_db)):
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    return crud.nearby_places(db, acc)


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


def _validate_status(value: str | None) -> None:
    if value is not None and value not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUSES)}")


@router.post("", response_model=schemas.AdminAccommodationOut, status_code=201)
def create_accommodation(
    payload: schemas.AccommodationCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    _validate_status(payload.status)

    type_obj = db.query(models.AccommodationType).filter_by(code=payload.type_code).first()
    if not type_obj:
        raise HTTPException(status_code=400, detail=f"Unknown type_code '{payload.type_code}'")
    district_obj = db.query(models.District).filter_by(name=payload.district_name).first()
    if not district_obj:
        raise HTTPException(status_code=400, detail=f"Unknown district_name '{payload.district_name}'")

    amenity_objs = (
        db.query(models.Amenity).filter(models.Amenity.code.in_(payload.amenity_codes)).all()
        if payload.amenity_codes
        else []
    )

    acc = models.Accommodation(
        name=payload.name,
        type_id=type_obj.id,
        district_id=district_obj.id,
        description=payload.description,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        google_maps_url=payload.google_maps_url,
        price_per_night=payload.price_per_night,
        landmark_distance_km=payload.landmark_distance_km,
        phone=payload.phone,
        contact_line=payload.contact_line,
        contact_facebook=payload.contact_facebook,
        contact_instagram=payload.contact_instagram,
        website_url=payload.website_url,
        checkin_time=payload.checkin_time,
        checkout_time=payload.checkout_time,
        cancellation_policy=payload.cancellation_policy,
        min_age=payload.min_age,
        smoking_allowed=payload.smoking_allowed,
        deposit_required=payload.deposit_required,
        deposit_note=payload.deposit_note,
        payment_methods_json=payload.payment_methods or None,
        deposit_amount=payload.deposit_amount,
        deposit_percent=payload.deposit_percent,
        advance_booking_required=payload.advance_booking_required,
        advance_booking_days=payload.advance_booking_days,
        price_conditions=payload.price_conditions,
        recommended_reason=payload.recommended_reason,
        tags_json=payload.tags,
        status=payload.status,
        last_verified_at=payload.last_verified_at,
        source_note=payload.source_note,
        is_featured=payload.is_featured,
        amenities=amenity_objs,
        # images are managed exclusively through /api/admin/accommodations/{id}/images
        # (see app/routers/images.py) — never bundled into this form's save.
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)

    search_index.build_index(db)  # keep the semantic index in sync
    return crud.to_admin_accommodation_out(acc)


@router.put("/{accommodation_id}", response_model=schemas.AdminAccommodationOut)
def update_accommodation(
    accommodation_id: int,
    payload: schemas.AccommodationUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    _validate_status(payload.status)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    data = payload.model_dump(exclude_unset=True)

    type_code = data.pop("type_code", None)
    if type_code is not None:
        type_obj = db.query(models.AccommodationType).filter_by(code=type_code).first()
        if not type_obj:
            raise HTTPException(status_code=400, detail=f"Unknown type_code '{type_code}'")
        acc.type_id = type_obj.id

    district_name = data.pop("district_name", None)
    if district_name is not None:
        district_obj = db.query(models.District).filter_by(name=district_name).first()
        if not district_obj:
            raise HTTPException(status_code=400, detail=f"Unknown district_name '{district_name}'")
        acc.district_id = district_obj.id

    amenity_codes = data.pop("amenity_codes", None)
    tags = data.pop("tags", None)
    if tags is not None:
        acc.tags_json = tags
    payment_methods = data.pop("payment_methods", None)
    if payment_methods is not None:
        acc.payment_methods_json = payment_methods
    # images are managed exclusively through /api/admin/accommodation-images/*
    # (see app/routers/images.py) — this form never touches the gallery.
    data.pop("images", None)

    for field, value in data.items():
        setattr(acc, field, value)
    if amenity_codes is not None:
        acc.amenities = db.query(models.Amenity).filter(models.Amenity.code.in_(amenity_codes)).all()

    db.commit()
    db.refresh(acc)
    search_index.build_index(db)
    return crud.to_admin_accommodation_out(acc)


@router.delete("/{accommodation_id}", status_code=204)
def delete_accommodation(
    accommodation_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    db.delete(acc)
    db.commit()
    search_index.build_index(db)
