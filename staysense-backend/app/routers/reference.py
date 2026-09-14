from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/amenities", response_model=list[schemas.AmenityOut])
def list_amenities(db: Session = Depends(get_db)):
    return db.query(models.Amenity).order_by(models.Amenity.id).all()


@router.get("/accommodation-types", response_model=list[schemas.AccommodationTypeOut])
def list_accommodation_types(db: Session = Depends(get_db)):
    return db.query(models.AccommodationType).order_by(models.AccommodationType.id).all()
