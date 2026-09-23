from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-accommodation-places"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("/accommodations/{accommodation_id}/nearby-all", response_model=list[schemas.AdminNearbyPlaceOut])
def list_admin_nearby_places(
    accommodation_id: int,
    radius_km: float = 12.0,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Every place within radius — curated links plus live haversine
    estimates — grouped/rendered by category on the admin side, mirroring
    the public "สถานที่ใกล้เคียง" modal so the admin can browse the exact
    same view a visitor sees and curate any entry from it."""
    _require_admin(user)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    return crud.admin_nearby_places(db, acc, radius_km=radius_km)


@router.get("/accommodations/{accommodation_id}/places", response_model=list[schemas.AccommodationPlaceOut])
def list_admin_accommodation_places(
    accommodation_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Every curated place link for this accommodation — the same rows
    crud.nearby_places prefers over a live haversine estimate on the public
    site."""
    _require_admin(user)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    rows = (
        db.query(models.AccommodationPlace)
        .options(joinedload(models.AccommodationPlace.place))
        .filter(models.AccommodationPlace.accommodation_id == accommodation_id)
        .join(models.Place)
        .order_by(models.Place.name)
        .all()
    )
    return [crud.to_accommodation_place_out(ap) for ap in rows]


@router.post("/accommodations/{accommodation_id}/places", response_model=schemas.AccommodationPlaceOut, status_code=201)
def create_admin_accommodation_place(
    accommodation_id: int,
    payload: schemas.AccommodationPlaceCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    place = db.get(models.Place, payload.place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    ap = models.AccommodationPlace(accommodation_id=accommodation_id, **payload.model_dump())
    db.add(ap)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="สถานที่นี้ถูกเชื่อมกับที่พักนี้ไว้แล้ว")
    db.refresh(ap)
    return crud.to_accommodation_place_out(ap)


@router.put("/accommodation-places/{link_id}", response_model=schemas.AccommodationPlaceOut)
def update_admin_accommodation_place(
    link_id: int,
    payload: schemas.AccommodationPlaceUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    ap = db.get(models.AccommodationPlace, link_id)
    if not ap:
        raise HTTPException(status_code=404, detail="Link not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ap, field, value)
    db.commit()
    db.refresh(ap)
    return crud.to_accommodation_place_out(ap)


@router.delete("/accommodation-places/{link_id}", status_code=204)
def delete_admin_accommodation_place(
    link_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    ap = db.get(models.AccommodationPlace, link_id)
    if not ap:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(ap)
    db.commit()
