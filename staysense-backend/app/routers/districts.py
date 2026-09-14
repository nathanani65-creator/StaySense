from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/districts", tags=["districts"])


@router.get("", response_model=list[schemas.DistrictOut])
def list_districts(db: Session = Depends(get_db)):
    return db.query(models.District).order_by(models.District.name).all()


@router.get("/counts", response_model=schemas.DistrictCountsOut)
def get_district_counts(
    type: str | None = Query(default=None),
    price_min: float | None = None,
    price_max: float | None = None,
    rating_min: float | None = None,
    amenities: list[str] = Query(default=[]),
    distance_max_km: float | None = None,
    db: Session = Depends(get_db),
):
    counts = crud.district_counts(
        db,
        type_code=type,
        price_min=price_min,
        price_max=price_max,
        rating_min=rating_min,
        amenity_codes=amenities or None,
        distance_max_km=distance_max_km,
    )
    return schemas.DistrictCountsOut(counts=counts)
