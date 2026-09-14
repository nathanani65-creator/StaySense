from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/accommodations/{accommodation_id}/reviews", tags=["reviews"])


def _get_accommodation_or_404(db: Session, accommodation_id: int) -> models.Accommodation:
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    return acc


@router.get("", response_model=schemas.ReviewListOut)
def list_reviews(
    accommodation_id: int,
    sort: str = Query(default="newest", pattern="^(newest|highest|lowest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    _get_accommodation_or_404(db, accommodation_id)

    q = (
        db.query(models.Review)
        .options(joinedload(models.Review.user))
        .filter(models.Review.accommodation_id == accommodation_id)
    )
    total = q.count()

    if sort == "highest":
        q = q.order_by(models.Review.rating.desc(), models.Review.created_at.desc())
    elif sort == "lowest":
        q = q.order_by(models.Review.rating.asc(), models.Review.created_at.desc())
    else:
        q = q.order_by(models.Review.created_at.desc())

    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return schemas.ReviewListOut(
        items=[crud.to_review_out(r) for r in items],
        total=total,
        page=page,
        pageSize=page_size,
    )


@router.post("", response_model=schemas.ReviewOut, status_code=201)
def create_review(
    accommodation_id: int,
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    _get_accommodation_or_404(db, accommodation_id)

    review = models.Review(
        accommodation_id=accommodation_id,
        user_id=user.id,
        rating=payload.rating,
        cleanliness_rating=payload.cleanliness_rating,
        location_rating=payload.location_rating,
        service_rating=payload.service_rating,
        value_rating=payload.value_rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    # the AFTER INSERT trigger (schema_addendum_3.sql) has already updated
    # the accommodation's rating_avg / review_count / category averages
    return crud.to_review_out(review)
