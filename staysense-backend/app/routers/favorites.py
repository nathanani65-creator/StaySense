from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=list[schemas.AccommodationOut])
def list_favorites(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    favs = db.query(models.Favorite).filter_by(user_id=user.id).all()
    acc_ids = [f.accommodation_id for f in favs]
    accs = db.query(models.Accommodation).filter(models.Accommodation.id.in_(acc_ids)).all()
    out = []
    for acc in accs:
        item = crud.to_accommodation_out(acc)
        item.fav = True
        out.append(item)
    return out


@router.post("/{accommodation_id}", status_code=201)
def add_favorite(accommodation_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")

    existing = db.query(models.Favorite).filter_by(user_id=user.id, accommodation_id=accommodation_id).first()
    if existing:
        return {"ok": True}

    db.add(models.Favorite(user_id=user.id, accommodation_id=accommodation_id))
    db.commit()
    crud.log_event(db, accommodation_id=accommodation_id, user_id=user.id, event_type="favorite")
    return {"ok": True}


@router.delete("/{accommodation_id}", status_code=204)
def remove_favorite(accommodation_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fav = db.query(models.Favorite).filter_by(user_id=user.id, accommodation_id=accommodation_id).first()
    if fav:
        db.delete(fav)
        db.commit()
