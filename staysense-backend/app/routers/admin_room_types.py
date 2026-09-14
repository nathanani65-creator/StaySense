from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-room-types"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _apply_room_type_fields(rt: models.RoomType, data: dict) -> None:
    """Shared create/update field mapping — pulls out room_amenities (->
    _json) and setattrs the rest. Images are deliberately NOT handled here:
    they're managed exclusively through /api/admin/room-types/{id}/images
    (see app/routers/images.py), so saving this form never touches the
    room type's gallery."""
    amenities = data.pop("room_amenities", None)
    if amenities is not None:
        rt.room_amenities_json = amenities
    data.pop("images", None)
    for field, value in data.items():
        setattr(rt, field, value)


@router.get("/accommodations/{accommodation_id}/room-types", response_model=list[schemas.RoomTypeOut])
def list_admin_room_types(
    accommodation_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Every room type for this accommodation, including hidden ones — the
    public detail endpoint filters those out (see crud.to_room_type_out)."""
    _require_admin(user)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    return [crud.to_room_type_out(rt) for rt in sorted(acc.room_types, key=lambda r: r.sort_order)]


@router.post("/accommodations/{accommodation_id}/room-types", response_model=schemas.RoomTypeOut, status_code=201)
def create_admin_room_type(
    accommodation_id: int,
    payload: schemas.RoomTypeCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    data = payload.model_dump()
    rt = models.RoomType(accommodation_id=accommodation_id)
    _apply_room_type_fields(rt, data)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return crud.to_room_type_out(rt)


@router.put("/room-types/{room_type_id}", response_model=schemas.RoomTypeOut)
def update_admin_room_type(
    room_type_id: int,
    payload: schemas.RoomTypeUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    rt = db.get(models.RoomType, room_type_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Room type not found")

    data = payload.model_dump(exclude_unset=True)
    _apply_room_type_fields(rt, data)
    db.commit()
    db.refresh(rt)
    return crud.to_room_type_out(rt)


@router.delete("/room-types/{room_type_id}", status_code=204)
def delete_admin_room_type(
    room_type_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    rt = db.get(models.RoomType, room_type_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Room type not found")
    db.delete(rt)
    db.commit()
