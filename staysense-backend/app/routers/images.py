"""Image management: two strictly separate galleries.

- accommodation_images, keyed by accommodation_id — the whole-property gallery.
- room_type_images, keyed by room_type_id — one gallery per room/house/villa type.

Never mixed: no endpoint here ever returns both groups together, and every
query is scoped to exactly one owner id. See schema_addendum_18.sql and
app/image_files.py for the storage/DB side of this.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from sqlalchemy.orm import Session

from .. import crud, image_files, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api", tags=["images"])


def _require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def _validate_status(value: str | None) -> None:
    if value is not None and value not in schemas.IMAGE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(schemas.IMAGE_STATUSES)}")


@router.get("/image-categories", response_model=schemas.ImageCategoriesOut)
def get_image_categories():
    return schemas.ImageCategoriesOut(
        accommodation=[schemas.ImageCategoryOut(key=k, label=v) for k, v in schemas.ACCOMMODATION_IMAGE_CATEGORIES],
        roomType=[schemas.ImageCategoryOut(key=k, label=v) for k, v in schemas.ROOM_IMAGE_CATEGORIES],
    )


# ------------------------------------------------------- accommodation gallery

def _get_accommodation_or_404(db: Session, accommodation_id: int) -> models.Accommodation:
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    return acc


def _sorted_images(images, *, published_only: bool):
    rows = [i for i in images if not published_only or i.status == "published"]
    return sorted(rows, key=lambda i: (not i.is_cover, i.sort_order))


@router.get("/accommodations/{accommodation_id}/images", response_model=list[schemas.AccommodationImageOut])
def list_accommodation_images(accommodation_id: int, db: Session = Depends(get_db)):
    acc = _get_accommodation_or_404(db, accommodation_id)
    return _sorted_images(acc.images, published_only=True)


@router.get("/admin/accommodations/{accommodation_id}/images", response_model=list[schemas.AccommodationImageOut])
def admin_list_accommodation_images(
    accommodation_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    acc = _get_accommodation_or_404(db, accommodation_id)
    return _sorted_images(acc.images, published_only=False)


@router.post("/admin/accommodations/{accommodation_id}/images", response_model=list[schemas.AccommodationImageOut], status_code=201)
async def upload_accommodation_images(
    accommodation_id: int,
    files: list[UploadFile] = File(...),
    category: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    acc = _get_accommodation_or_404(db, accommodation_id)
    image_files.validate_upload_batch(files)

    owner_code = f"acc_{acc.external_code or f'ACC{acc.id}'}"
    created: list[models.AccommodationImage] = []
    next_order = crud.next_display_order(db, models.AccommodationImage, models.AccommodationImage.accommodation_id, accommodation_id)
    for f in files:
        raw = await f.read()
        saved = image_files.save_image_upload(raw, f.content_type, group="accommodations", owner_code=owner_code)
        row = models.AccommodationImage(
            accommodation_id=accommodation_id,
            image_url=saved["url"],
            thumbnail_url=saved["thumbnailUrl"],
            image_category=category,
            sort_order=next_order,
            status="published",
            uploaded_by=user.id,
        )
        next_order += 1
        db.add(row)
        created.append(row)

    db.flush()
    crud.ensure_group_has_cover(db, models.AccommodationImage, models.AccommodationImage.accommodation_id, accommodation_id)
    db.commit()
    for row in created:
        db.refresh(row)
        crud.log_image_audit(
            db, admin_user_id=user.id, action="create", image_group="accommodation",
            accommodation_id=accommodation_id, image_id=row.id, new_value={"url": row.image_url},
        )
    return _sorted_images(acc.images, published_only=False)


@router.patch("/admin/accommodation-images/reorder", status_code=204)
def reorder_accommodation_images(
    payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    accommodation_id = payload.get("accommodationId")
    ordered_ids = payload.get("orderedIds") or []
    if not accommodation_id:
        raise HTTPException(status_code=400, detail="accommodationId is required")
    _get_accommodation_or_404(db, accommodation_id)
    crud.reorder_images(db, models.AccommodationImage, models.AccommodationImage.accommodation_id, accommodation_id, ordered_ids)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="reorder", image_group="accommodation",
        accommodation_id=accommodation_id, image_id=0, new_value={"orderedIds": ordered_ids},
    )


def _get_accommodation_image_or_404(db: Session, image_id: int) -> models.AccommodationImage:
    img = db.get(models.AccommodationImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return img


@router.patch("/admin/accommodation-images/{image_id}", response_model=schemas.AccommodationImageOut)
def update_accommodation_image(
    image_id: int, payload: schemas.ImageMetaPatch, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    _validate_status(payload.status)
    img = _get_accommodation_image_or_404(db, image_id)
    old_value = {"category": img.image_category, "caption": img.caption, "altText": img.alt_text,
                 "sourceName": img.source_name, "sourceUrl": img.source_url, "status": img.status}

    data = payload.model_dump(exclude_unset=True)
    if "category" in data:
        img.image_category = data["category"]
    if "caption" in data:
        img.caption = data["caption"]
    if "altText" in data:
        img.alt_text = data["altText"]
    if "sourceName" in data:
        img.source_name = data["sourceName"]
    if "sourceUrl" in data:
        img.source_url = data["sourceUrl"]
    if "status" in data and data["status"] is not None:
        img.status = data["status"]
        if img.status != "published" and img.is_cover:
            img.is_cover = False
            crud.ensure_group_has_cover(db, models.AccommodationImage, models.AccommodationImage.accommodation_id, img.accommodation_id)

    db.commit()
    db.refresh(img)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="update", image_group="accommodation",
        accommodation_id=img.accommodation_id, image_id=img.id, old_value=old_value, new_value=data,
    )
    return img


@router.patch("/admin/accommodation-images/{image_id}/cover", response_model=schemas.AccommodationImageOut)
def set_accommodation_image_cover(
    image_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    img = _get_accommodation_image_or_404(db, image_id)
    crud.set_cover(db, models.AccommodationImage, models.AccommodationImage.accommodation_id, img.accommodation_id, image_id)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="cover", image_group="accommodation",
        accommodation_id=img.accommodation_id, image_id=image_id,
    )
    return img


@router.delete("/admin/accommodation-images/{image_id}", status_code=204)
def delete_accommodation_image(
    image_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    img = _get_accommodation_image_or_404(db, image_id)
    acc_id = img.accommodation_id
    was_cover = img.is_cover
    crud.soft_delete_image(db, models.AccommodationImage, models.AccommodationImage.accommodation_id, acc_id, image_id)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="delete", image_group="accommodation",
        accommodation_id=acc_id, image_id=image_id, old_value={"wasCover": was_cover},
    )


# ------------------------------------------------------------- room-type gallery

def _get_room_type_or_404(db: Session, room_type_id: int) -> models.RoomType:
    rt = db.get(models.RoomType, room_type_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Room type not found")
    return rt


@router.get("/room-types/{room_type_id}/images", response_model=list[schemas.RoomTypeImageOut])
def list_room_type_images(room_type_id: int, db: Session = Depends(get_db)):
    rt = _get_room_type_or_404(db, room_type_id)
    return _sorted_images(rt.images, published_only=True)


@router.get("/admin/room-types/{room_type_id}/images", response_model=list[schemas.RoomTypeImageOut])
def admin_list_room_type_images(
    room_type_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    rt = _get_room_type_or_404(db, room_type_id)
    return _sorted_images(rt.images, published_only=False)


@router.post("/admin/room-types/{room_type_id}/images", response_model=list[schemas.RoomTypeImageOut], status_code=201)
async def upload_room_type_images(
    room_type_id: int,
    files: list[UploadFile] = File(...),
    category: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _require_admin(user)
    rt = _get_room_type_or_404(db, room_type_id)
    image_files.validate_upload_batch(files)

    owner_code = f"room_{rt.external_code or f'ROOM{rt.id}'}"
    created: list[models.RoomTypeImage] = []
    next_order = crud.next_display_order(db, models.RoomTypeImage, models.RoomTypeImage.room_type_id, room_type_id)
    for f in files:
        raw = await f.read()
        saved = image_files.save_image_upload(raw, f.content_type, group="room_types", owner_code=owner_code)
        row = models.RoomTypeImage(
            room_type_id=room_type_id,
            image_url=saved["url"],
            thumbnail_url=saved["thumbnailUrl"],
            image_category=category,
            sort_order=next_order,
            status="published",
            uploaded_by=user.id,
        )
        next_order += 1
        db.add(row)
        created.append(row)

    db.flush()
    crud.ensure_group_has_cover(db, models.RoomTypeImage, models.RoomTypeImage.room_type_id, room_type_id)
    db.commit()
    for row in created:
        db.refresh(row)
        crud.log_image_audit(
            db, admin_user_id=user.id, action="create", image_group="room_type",
            room_type_id=room_type_id, image_id=row.id, new_value={"url": row.image_url},
        )
    return _sorted_images(rt.images, published_only=False)


@router.patch("/admin/room-type-images/reorder", status_code=204)
def reorder_room_type_images(
    payload: dict, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    room_type_id = payload.get("roomTypeId")
    ordered_ids = payload.get("orderedIds") or []
    if not room_type_id:
        raise HTTPException(status_code=400, detail="roomTypeId is required")
    _get_room_type_or_404(db, room_type_id)
    crud.reorder_images(db, models.RoomTypeImage, models.RoomTypeImage.room_type_id, room_type_id, ordered_ids)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="reorder", image_group="room_type",
        room_type_id=room_type_id, image_id=0, new_value={"orderedIds": ordered_ids},
    )


def _get_room_type_image_or_404(db: Session, image_id: int) -> models.RoomTypeImage:
    img = db.get(models.RoomTypeImage, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return img


@router.patch("/admin/room-type-images/{image_id}", response_model=schemas.RoomTypeImageOut)
def update_room_type_image(
    image_id: int, payload: schemas.ImageMetaPatch, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    _validate_status(payload.status)
    img = _get_room_type_image_or_404(db, image_id)
    old_value = {"category": img.image_category, "caption": img.caption, "altText": img.alt_text,
                 "sourceName": img.source_name, "sourceUrl": img.source_url, "status": img.status}

    data = payload.model_dump(exclude_unset=True)
    if "category" in data:
        img.image_category = data["category"]
    if "caption" in data:
        img.caption = data["caption"]
    if "altText" in data:
        img.alt_text = data["altText"]
    if "sourceName" in data:
        img.source_name = data["sourceName"]
    if "sourceUrl" in data:
        img.source_url = data["sourceUrl"]
    if "status" in data and data["status"] is not None:
        img.status = data["status"]
        if img.status != "published" and img.is_cover:
            img.is_cover = False
            crud.ensure_group_has_cover(db, models.RoomTypeImage, models.RoomTypeImage.room_type_id, img.room_type_id)

    db.commit()
    db.refresh(img)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="update", image_group="room_type",
        room_type_id=img.room_type_id, image_id=img.id, old_value=old_value, new_value=data,
    )
    return img


@router.patch("/admin/room-type-images/{image_id}/cover", response_model=schemas.RoomTypeImageOut)
def set_room_type_image_cover(
    image_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    img = _get_room_type_image_or_404(db, image_id)
    crud.set_cover(db, models.RoomTypeImage, models.RoomTypeImage.room_type_id, img.room_type_id, image_id)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="cover", image_group="room_type",
        room_type_id=img.room_type_id, image_id=image_id,
    )
    return img


@router.delete("/admin/room-type-images/{image_id}", status_code=204)
def delete_room_type_image(
    image_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    _require_admin(user)
    img = _get_room_type_image_or_404(db, image_id)
    room_type_id = img.room_type_id
    was_cover = img.is_cover
    crud.soft_delete_image(db, models.RoomTypeImage, models.RoomTypeImage.room_type_id, room_type_id, image_id)
    crud.log_image_audit(
        db, admin_user_id=user.id, action="delete", image_group="room_type",
        room_type_id=room_type_id, image_id=image_id, old_value={"wasCover": was_cover},
    )
