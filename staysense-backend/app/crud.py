from datetime import date, timedelta
from math import radians, sin, cos, asin, sqrt

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from urllib.parse import quote

from . import models, schemas

# Shown wherever an accommodation has zero real published images — never a
# broken-image icon or empty space (spec: image-management system §13).
_FALLBACK_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='800' height='500'>"
    "<rect width='800' height='500' fill='#EEECFF'/>"
    "<text x='400' y='260' font-family='sans-serif' font-size='22' fill='#7C6FE0' "
    "text-anchor='middle'>ยังไม่มีรูปภาพ</text>"
    "</svg>"
)
FALLBACK_IMAGE_URL = "data:image/svg+xml;utf8," + quote(_FALLBACK_SVG)


def user_favorite_ids(db: Session, user: models.User | None) -> set[int]:
    """Accommodation ids the given user has favorited — empty set for an
    anonymous (not logged in) caller."""
    if not user:
        return set()
    rows = db.query(models.Favorite.accommodation_id).filter_by(user_id=user.id).all()
    return {r[0] for r in rows}


def apply_fav_flags(items, fav_ids: set[int]):
    """Sets `.fav` on a list of AccommodationOut/AccommodationDetailOut
    (or a single one) from a real per-user favorites lookup — never the
    unconditional False that to_accommodation_out() defaults to."""
    single = not isinstance(items, list)
    seq = [items] if single else items
    for item in seq:
        item.fav = item.id in fav_ids
    return seq[0] if single else seq


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (float(lat1), float(lon1), float(lat2), float(lon2)))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def nearby_places(db: Session, acc: models.Accommodation, *, radius_km: float = 12.0):
    """Places near the accommodation. A place with a curated
    AccommodationPlace row (real, manually-verified distance from the data
    collection spreadsheet) always uses that distance and is always
    included; every other place falls back to a live haversine straight-line
    estimate, filtered to `radius_km`."""
    curated = (
        db.query(models.AccommodationPlace)
        .options(joinedload(models.AccommodationPlace.place))
        .filter(models.AccommodationPlace.accommodation_id == acc.id)
        .all()
    )
    curated_place_ids = {c.place_id for c in curated}

    rows = [(float(c.distance_km), c.place) for c in curated if c.distance_km is not None]

    if acc.latitude is not None and acc.longitude is not None:
        for p in db.query(models.Place).all():
            if p.id in curated_place_ids:
                continue
            d = round(haversine_km(acc.latitude, acc.longitude, p.latitude, p.longitude), 2)
            if d <= radius_km:
                rows.append((d, p))
    elif not rows:
        return schemas.NearbyOut(popular=[], nearest=[], all=[])

    rows.sort(key=lambda r: r[0])

    def out(p, d):
        return schemas.PlaceOut(name=p.name, category=p.category, distanceKm=d)

    return schemas.NearbyOut(
        popular=[out(p, d) for d, p in rows if p.is_popular][:5],
        nearest=[out(p, d) for d, p in rows][:6],
        all=[out(p, d) for d, p in rows],
    )


def to_accommodation_out(acc: models.Accommodation) -> schemas.AccommodationOut:
    published_images = sorted(
        (i for i in acc.images if i.status == "published"), key=lambda i: (not i.is_cover, i.sort_order)
    )
    img = published_images[0].image_url if published_images else FALLBACK_IMAGE_URL
    maps_url = acc.google_maps_url
    if not maps_url and acc.latitude is not None and acc.longitude is not None:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={acc.latitude},{acc.longitude}"
    return schemas.AccommodationOut(
        id=acc.id,
        name=acc.name,
        district=acc.district.name,
        type=acc.type.name_th,
        typeCode=acc.type.code,
        price=float(acc.price_per_night),
        rating=float(acc.rating_avg),
        reviews=acc.review_count,
        distanceKm=float(acc.landmark_distance_km) if acc.landmark_distance_km is not None else None,
        landmark=acc.district.landmark_name,
        amenities=[a.code for a in acc.amenities],
        tags=acc.tags_json or [],
        reason=acc.recommended_reason,
        img=img,
        fav=False,  # per-user; overridden by the router when a user is authenticated
        googleMapsUrl=maps_url,
    )


def to_room_type_out(rt: models.RoomType) -> schemas.RoomTypeOut:
    return schemas.RoomTypeOut(
        id=rt.id,
        name=rt.name,
        price=float(rt.price_per_night),
        maxOccupancy=rt.max_occupancy,
        standardOccupancy=rt.standard_occupancy,
        bedType=rt.bed_type,
        view=rt.view_type,
        roomSizeSqm=float(rt.room_size_sqm) if rt.room_size_sqm is not None else None,
        breakfastIncluded=rt.breakfast_included,
        extraBedAvailable=rt.extra_bed_available,
        extraBedPrice=float(rt.extra_bed_price) if rt.extra_bed_price is not None else None,
        extraBedMax=rt.extra_bed_max,
        bedrooms=rt.bedrooms,
        bathrooms=rt.bathrooms,
        unitsAvailable=rt.units_available,
        childrenAllowed=rt.children_allowed,
        smokingAllowed=rt.smoking_allowed,
        petsAllowed=rt.pets_allowed,
        description=rt.description,
        roomAmenities=rt.room_amenities_json or [],
        images=[
            schemas.ImageOut(url=i.image_url, caption=i.caption, sourceNote=i.source_note, isCover=i.is_cover)
            for i in sorted(
                (img for img in rt.images if img.status == "published"),
                key=lambda i: (not i.is_cover, i.sort_order),
            )
        ],
        isVisible=rt.is_visible,
    )


def to_accommodation_detail_out(
    acc: models.Accommodation, *, include_hidden_rooms: bool = False
) -> schemas.AccommodationDetailOut:
    base = to_accommodation_out(acc)
    images = [
        schemas.ImageOut(url=i.image_url, caption=i.caption, sourceNote=i.source_note, isCover=i.is_cover)
        for i in sorted(
            (img for img in acc.images if img.status == "published"),
            key=lambda i: (not i.is_cover, i.sort_order),
        )
    ] or ([schemas.ImageOut(url=base.img, isCover=True)] if base.img else [])
    room_types = [
        to_room_type_out(rt) for rt in acc.room_types if include_hidden_rooms or rt.is_visible
    ]
    policies = schemas.PoliciesOut(
        checkinTime=acc.checkin_time,
        checkoutTime=acc.checkout_time,
        cancellationPolicy=acc.cancellation_policy,
        minAge=acc.min_age,
        smokingAllowed=acc.smoking_allowed,
        depositRequired=acc.deposit_required,
        depositNote=acc.deposit_note,
        depositAmount=float(acc.deposit_amount) if acc.deposit_amount is not None else None,
        depositPercent=acc.deposit_percent,
        advanceBookingRequired=acc.advance_booking_required,
        advanceBookingDays=acc.advance_booking_days,
        priceConditions=acc.price_conditions,
        paymentMethods=acc.payment_methods_json or [],
    )
    contact = schemas.ContactOut(
        phone=acc.phone,
        line=acc.contact_line,
        facebook=acc.contact_facebook,
        instagram=acc.contact_instagram,
        website=acc.website_url,
    )
    category_ratings = schemas.CategoryRatingsOut(
        cleanliness=float(acc.rating_cleanliness),
        location=float(acc.rating_location),
        service=float(acc.rating_service),
        value=float(acc.rating_value),
    )
    return schemas.AccommodationDetailOut(
        **base.model_dump(),
        description=acc.description,
        address=acc.address,
        phone=acc.phone,
        latitude=float(acc.latitude) if acc.latitude is not None else None,
        longitude=float(acc.longitude) if acc.longitude is not None else None,
        images=images,
        roomTypes=room_types,
        contact=contact,
        policies=policies,
        categoryRatings=category_ratings,
        status=acc.status,
        lastVerifiedAt=acc.last_verified_at,
        sourceNote=acc.source_note,
        isFeatured=acc.is_featured,
    )


def to_admin_accommodation_out(acc: models.Accommodation) -> schemas.AdminAccommodationOut:
    base = to_accommodation_out(acc)
    return schemas.AdminAccommodationOut(
        **base.model_dump(),
        status=acc.status,
        lastVerifiedAt=acc.last_verified_at,
        updatedAt=acc.updated_at,
        isFeatured=acc.is_featured,
    )


def log_search(
    db: Session,
    *,
    user_id: int | None,
    query_text: str,
    price_ceiling: float | None,
    district_id: int | None,
    result_count: int,
    accommodation_type: str | None = None,
    facilities: list[str] | None = None,
    radius_km: float | None = None,
    sort_by: str | None = None,
    use_current_location: bool = False,
    normalized_query: str | None = None,
    detected_intent: dict | None = None,
    confidence: float | None = None,
    save_history: bool = True,
) -> None:
    # Real coordinates are never written here — only aggregate, non-identifying
    # query metadata (type/facilities/radius/sort + whether location was used).
    # A member who turned off save_search_history is skipped entirely — not
    # logged anonymously, not logged and later hidden, just never written.
    if not save_history:
        return
    db.add(
        models.SearchLog(
            user_id=user_id,
            query_text=query_text,
            normalized_query=normalized_query,
            detected_intent_json=detected_intent,
            confidence=confidence,
            extracted_price_max=price_ceiling,
            extracted_district_id=district_id,
            result_count=result_count,
            accommodation_type=accommodation_type,
            facilities_json=facilities or None,
            radius_km=radius_km,
            sort_by=sort_by,
            use_current_location=use_current_location,
        )
    )
    db.commit()


def format_distance_th(km: float, *, is_road: bool = False) -> str:
    """Thai-formatted distance string per spec §13: meters under 1km, one
    decimal place in km otherwise, tagged with whether it's a real routed
    distance or a straight-line estimate — never an unlabeled number."""
    value = f"{round(km * 1000)} เมตร" if km < 1 else f"{round(km, 1)} กม."
    suffix = "ระยะทางตามเส้นทาง" if is_road else "ระยะเส้นตรงโดยประมาณ"
    return f"{value} ({suffix})"


def resolve_place_distance(db: Session, acc: models.Accommodation, place: models.Place) -> tuple[float, bool] | None:
    """Real distance from `acc` to a specific `place`: prefers a curated,
    manually-verified accommodation_places row (labeled a road distance when
    it carries a travel_method), else a live haversine straight-line
    fallback when both have coordinates. Returns None — never a fabricated
    number — when neither source has real data (spec §15)."""
    curated = (
        db.query(models.AccommodationPlace)
        .filter_by(accommodation_id=acc.id, place_id=place.id)
        .first()
    )
    if curated and curated.distance_km is not None:
        return float(curated.distance_km), bool(curated.travel_method)
    if acc.latitude is not None and acc.longitude is not None:
        return round(haversine_km(acc.latitude, acc.longitude, place.latitude, place.longitude), 2), False
    return None


def admin_list_members(
    db: Session, *, search: str | None = None, page: int = 1, page_size: int = 20
) -> schemas.AdminMemberListOut:
    fav_counts = dict(
        db.query(models.Favorite.user_id, func.count(models.Favorite.id))
        .group_by(models.Favorite.user_id)
        .all()
    )
    stmt = db.query(models.User)
    if search:
        stmt = stmt.filter(
            (models.User.name.ilike(f"%{search}%")) | (models.User.email.ilike(f"%{search}%"))
        )
    total = stmt.count()
    users = stmt.order_by(models.User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        schemas.AdminMemberOut(
            id=u.id, name=u.name, email=u.email, role=u.role, isActive=u.is_active,
            createdAt=u.created_at, favoriteCount=fav_counts.get(u.id, 0),
        )
        for u in users
    ]
    return schemas.AdminMemberListOut(items=items, total=total, page=page, pageSize=page_size)


def admin_stats(db: Session) -> schemas.AdminStatsOut:
    total_members = db.query(func.count(models.User.id)).filter(models.User.role == "user").scalar() or 0
    active_members = (
        db.query(func.count(models.User.id))
        .filter(models.User.role == "user", models.User.is_active.is_(True))
        .scalar()
        or 0
    )

    published = db.query(models.Accommodation).filter(models.Accommodation.status == "published")
    total_published = published.count()
    missing_verification = published.filter(models.Accommodation.last_verified_at.is_(None)).count()
    stale_cutoff = date.today() - timedelta(days=90)
    stale_verification = published.filter(
        models.Accommodation.last_verified_at.isnot(None),
        models.Accommodation.last_verified_at < stale_cutoff,
    ).count()

    top_favorited_rows = (
        db.query(models.Accommodation.id, models.Accommodation.name, func.count(models.Favorite.id).label("cnt"))
        .join(models.Favorite, models.Favorite.accommodation_id == models.Accommodation.id)
        .group_by(models.Accommodation.id, models.Accommodation.name)
        .order_by(func.count(models.Favorite.id).desc())
        .limit(5)
        .all()
    )
    top_favorited = [schemas.FavoritedAccommodationOut(id=r[0], name=r[1], favoriteCount=r[2]) for r in top_favorited_rows]

    total_searches = db.query(func.count(models.SearchLog.id)).scalar() or 0
    top_terms_rows = (
        db.query(models.SearchLog.query_text, func.count(models.SearchLog.id).label("cnt"))
        .group_by(models.SearchLog.query_text)
        .order_by(func.count(models.SearchLog.id).desc())
        .limit(10)
        .all()
    )
    no_result_rows = (
        db.query(models.SearchLog.query_text, func.count(models.SearchLog.id).label("cnt"))
        .filter(models.SearchLog.result_count == 0)
        .group_by(models.SearchLog.query_text)
        .order_by(func.count(models.SearchLog.id).desc())
        .limit(10)
        .all()
    )

    return schemas.AdminStatsOut(
        totalMembers=total_members,
        activeMembers=active_members,
        suspendedMembers=total_members - active_members,
        dataQuality=schemas.DataQualityOut(
            totalPublished=total_published,
            missingVerification=missing_verification,
            staleVerification=stale_verification,
        ),
        topFavorited=top_favorited,
        topSearchTerms=[schemas.SearchTermStatOut(term=t, count=c) for t, c in top_terms_rows],
        noResultSearchTerms=[schemas.SearchTermStatOut(term=t, count=c) for t, c in no_result_rows],
        totalSearches=total_searches,
        comparisonFeatureBuilt=False,
    )


def to_admin_place_out(place: models.Place) -> schemas.AdminPlaceOut:
    return schemas.AdminPlaceOut(
        id=place.id,
        name=place.name,
        category=place.category,
        latitude=float(place.latitude),
        longitude=float(place.longitude),
        address=place.address,
        isPopular=place.is_popular,
        sourceNote=place.source_note,
        districtName=place.district.name if place.district else None,
    )


def admin_list_places(
    db: Session, *, district_name: str | None = None, category: str | None = None, search: str | None = None
) -> list[schemas.AdminPlaceOut]:
    stmt = db.query(models.Place).options(joinedload(models.Place.district))
    if district_name:
        stmt = stmt.join(models.District).filter(models.District.name == district_name)
    if category:
        stmt = stmt.filter(models.Place.category == category)
    if search:
        stmt = stmt.filter(models.Place.name.ilike(f"%{search}%"))
    places = stmt.order_by(models.Place.name).all()
    return [to_admin_place_out(p) for p in places]


def admin_list_amenities(db: Session) -> list[schemas.AdminAmenityOut]:
    """Every amenity with how many accommodations currently use it, so an
    admin can see at a glance whether it's safe to retire one."""
    counts = dict(
        db.query(models.AccommodationAmenity.amenity_id, func.count(models.AccommodationAmenity.accommodation_id))
        .group_by(models.AccommodationAmenity.amenity_id)
        .all()
    )
    amenities = db.query(models.Amenity).order_by(models.Amenity.id).all()
    return [
        schemas.AdminAmenityOut(
            id=a.id,
            key=a.code,
            label=a.label_th,
            category=a.category,
            accommodationCount=counts.get(a.id, 0),
        )
        for a in amenities
    ]


def to_review_out(review: models.Review) -> schemas.ReviewOut:
    return schemas.ReviewOut(
        id=review.id,
        rating=review.rating,
        cleanlinessRating=review.cleanliness_rating,
        locationRating=review.location_rating,
        serviceRating=review.service_rating,
        valueRating=review.value_rating,
        comment=review.comment,
        createdAt=review.created_at,
        userName=review.user.name if review.user else (review.guest_name or "ผู้เข้าพัก"),
    )


def base_accommodation_query():
    return (
        select(models.Accommodation)
        .options(
            joinedload(models.Accommodation.district),
            joinedload(models.Accommodation.type),
            joinedload(models.Accommodation.amenities),
            joinedload(models.Accommodation.images),
        )
        .where(models.Accommodation.status == "published")
    )


def admin_list_accommodations(
    db: Session,
    *,
    status: str | None,
    district_name: str | None = None,
    type_code: str | None = None,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[models.Accommodation], int]:
    """Like list_accommodations, but for the admin table: every status
    (not just 'published'), optionally narrowed by status/district/type,
    plus a name search — newest-edited first."""
    stmt = (
        select(models.Accommodation)
        .options(
            joinedload(models.Accommodation.district),
            joinedload(models.Accommodation.type),
            joinedload(models.Accommodation.amenities),
            joinedload(models.Accommodation.images),
        )
    )
    if status:
        stmt = stmt.where(models.Accommodation.status == status)
    if district_name:
        stmt = stmt.join(models.District).where(models.District.name == district_name)
    if type_code:
        stmt = stmt.join(models.AccommodationType).where(models.AccommodationType.code == type_code)
    if search:
        stmt = stmt.where(models.Accommodation.name.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = stmt.order_by(models.Accommodation.updated_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).unique().all()
    return items, total or 0


def admin_district_type_counts(
    db: Session, *, status: str | None = None, search: str | None = None
) -> dict:
    """Count of accommodations per (district, accommodation type), for the
    admin summary grid — every status by default, so a stray draft/closed
    listing is still visible for audit, not silently excluded like the
    public district-counts endpoint."""
    districts = db.query(models.District).order_by(models.District.name).all()
    types = db.query(models.AccommodationType).order_by(models.AccommodationType.id).all()

    q = (
        select(models.District.name, models.AccommodationType.code, func.count(models.Accommodation.id))
        .select_from(models.Accommodation)
        .join(models.District, models.Accommodation.district_id == models.District.id)
        .join(models.AccommodationType, models.Accommodation.type_id == models.AccommodationType.id)
        .group_by(models.District.name, models.AccommodationType.code)
    )
    if status:
        q = q.where(models.Accommodation.status == status)
    if search:
        q = q.where(models.Accommodation.name.ilike(f"%{search}%"))

    raw = {(d, t): n for d, t, n in db.execute(q).all()}

    rows = []
    type_totals = {t.code: 0 for t in types}
    grand_total = 0
    for d in districts:
        counts = {}
        row_total = 0
        for t in types:
            n = raw.get((d.name, t.code), 0)
            counts[t.code] = n
            row_total += n
            type_totals[t.code] += n
        grand_total += row_total
        rows.append({"district": d.name, "counts": counts, "total": row_total})

    return {
        "typeCodes": [t.code for t in types],
        "typeLabels": {t.code: t.name_th for t in types},
        "rows": rows,
        "totals": type_totals,
        "grandTotal": grand_total,
    }


def apply_filters(
    stmt,
    *,
    type_code: str | None = None,
    district_names: list[str] | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    rating_min: float | None = None,
    amenity_codes: list[str] | None = None,
    distance_max_km: float | None = None,
    guest_count: int | None = None,
    smoking: bool | None = None,
    extra_bed: bool | None = None,
):
    if type_code:
        stmt = stmt.join(models.AccommodationType).where(models.AccommodationType.code == type_code)
    if district_names:
        stmt = stmt.join(models.District).where(models.District.name.in_(district_names))
    if price_min is not None:
        stmt = stmt.where(models.Accommodation.price_per_night >= price_min)
    if price_max is not None:
        stmt = stmt.where(models.Accommodation.price_per_night <= price_max)
    if rating_min is not None:
        stmt = stmt.where(models.Accommodation.rating_avg >= rating_min)
    if distance_max_km is not None:
        stmt = stmt.where(models.Accommodation.landmark_distance_km <= distance_max_km)
    if smoking is not None:
        stmt = stmt.where(models.Accommodation.smoking_allowed == smoking)
    if amenity_codes:
        # accommodation must have ALL requested amenities
        for code in amenity_codes:
            stmt = stmt.where(
                models.Accommodation.id.in_(
                    select(models.AccommodationAmenity.accommodation_id)
                    .join(models.Amenity)
                    .where(models.Amenity.code == code)
                )
            )
    if guest_count is not None:
        stmt = stmt.where(
            models.Accommodation.id.in_(
                select(models.RoomType.accommodation_id)
                .where(models.RoomType.max_occupancy >= guest_count)
            )
        )
    if extra_bed:
        stmt = stmt.where(
            models.Accommodation.id.in_(
                select(models.RoomType.accommodation_id)
                .where(models.RoomType.extra_bed_available.is_(True))
            )
        )
    return stmt


def apply_sort(stmt, sort: str | None):
    col = models.Accommodation
    if sort == "price-asc":
        return stmt.order_by(col.price_per_night.asc())
    if sort == "price-desc":
        return stmt.order_by(col.price_per_night.desc())
    if sort == "rating-desc":
        return stmt.order_by(col.rating_avg.desc())
    if sort == "distance-asc":
        return stmt.order_by(col.landmark_distance_km.asc())
    # 'recommended' (default): best rating, then closest
    return stmt.order_by(col.rating_avg.desc(), col.landmark_distance_km.asc())


def list_accommodations(
    db: Session,
    *,
    type_code: str | None,
    district_names: list[str] | None,
    price_min: float | None,
    price_max: float | None,
    rating_min: float | None,
    amenity_codes: list[str] | None,
    distance_max_km: float | None,
    sort: str | None,
    page: int,
    page_size: int,
) -> tuple[list[models.Accommodation], int]:
    stmt = base_accommodation_query()
    stmt = apply_filters(
        stmt,
        type_code=type_code,
        district_names=district_names,
        price_min=price_min,
        price_max=price_max,
        rating_min=rating_min,
        amenity_codes=amenity_codes,
        distance_max_km=distance_max_km,
    )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = apply_sort(stmt, sort)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).unique().all()
    return items, total or 0


def district_counts(
    db: Session,
    *,
    type_code: str | None,
    price_min: float | None,
    price_max: float | None,
    rating_min: float | None,
    amenity_codes: list[str] | None,
    distance_max_km: float | None,
) -> dict[str, int]:
    """Counts per district, ignoring the district filter itself (mirrors
    HotelsView.vue's districtCounts computed property)."""
    stmt = (
        select(models.District.name, func.count(models.Accommodation.id))
        .select_from(models.District)
        .outerjoin(
            models.Accommodation,
            (models.Accommodation.district_id == models.District.id)
            & (models.Accommodation.status == "published"),
        )
        .group_by(models.District.name)
    )
    # NOTE: applying non-district filters here requires a slightly different
    # join path; for simplicity we filter accommodations first, then count.
    sub = base_accommodation_query()
    sub = apply_filters(
        sub,
        type_code=type_code,
        district_names=None,
        price_min=price_min,
        price_max=price_max,
        rating_min=rating_min,
        amenity_codes=amenity_codes,
        distance_max_km=distance_max_km,
    ).subquery()

    stmt = (
        select(models.District.name, func.count(sub.c.id))
        .select_from(models.District)
        .outerjoin(sub, sub.c.district_id == models.District.id)
        .group_by(models.District.name)
    )
    rows = db.execute(stmt).all()
    return {name: count for name, count in rows}


# --------------------------------------------------------------------- home

POPULARITY_WINDOW_DAYS = 30
POPULARITY_MIN_EVENTS = 5
POPULARITY_MIN_ACCOMMODATIONS = 3
POPULARITY_WEIGHTS = {
    "view": 1,
    "favorite": 3,
    "compare": 2,
    "contact_click": 4,
    "direction_click": 2,
}
EVENT_LABELS = {
    "view": "เข้าชม",
    "favorite": "บันทึกเป็นรายการโปรด",
    "compare": "เพิ่มเพื่อเปรียบเทียบ",
    "contact_click": "กดดูช่องทางติดต่อ",
    "direction_click": "กดดูเส้นทาง",
}
ATMOSPHERE_KEYWORDS = {
    "quiet": ["เงียบสงบ", "เงียบ", "สงบ"],
    "nature": ["ธรรมชาติ", "สวน", "ป่า"],  # "ภูเขา"/"แม่น้ำ" are handled as a
    # distinct, data-verified "view" criterion (query_intent.VIEW_KEYWORDS),
    # not a fuzzy atmosphere-description match — keeps "วิวภูเขา" from also
    # firing a redundant/looser "บรรยากาศใกล้ชิดธรรมชาติ" reason (spec §7).
    "city": ["ใจกลางเมือง", "กลางเมือง", "ในเมือง"],
    "family": ["ครอบครัว"],
}


def log_event(db: Session, *, accommodation_id: int, user_id: int | None, event_type: str) -> None:
    if event_type not in schemas.EVENT_TYPES:
        return
    db.add(models.AccommodationEvent(accommodation_id=accommodation_id, user_id=user_id, event_type=event_type))
    db.commit()


def get_user_preference(db: Session, user_id: int) -> models.UserPreference | None:
    return db.get(models.UserPreference, user_id)


def save_user_preference(db: Session, user_id: int, payload: schemas.UserPreferenceIn) -> models.UserPreference:
    pref = db.get(models.UserPreference, user_id)
    if not pref:
        pref = models.UserPreference(user_id=user_id)
        db.add(pref)
    pref.type_codes = payload.type_codes or None
    pref.district_names = payload.district_names or None
    pref.budget_min = payload.budget_min
    pref.budget_max = payload.budget_max
    pref.guest_count = payload.guest_count
    pref.amenity_codes = payload.amenity_codes or None
    pref.atmosphere_codes = payload.atmosphere_codes or None
    pref.near_place_categories = payload.near_place_categories or None
    db.commit()
    db.refresh(pref)
    return pref


def has_personal_data(db: Session, user: models.User) -> bool:
    """Anything real to personalize from: explicit preferences, a favorite,
    a viewed accommodation, or (if the member allows it) search history."""
    if db.get(models.UserPreference, user.id):
        return True
    if db.query(models.Favorite).filter_by(user_id=user.id).first():
        return True
    if db.query(models.AccommodationEvent).filter_by(user_id=user.id, event_type="view").first():
        return True
    if user.allow_personalization and db.query(models.SearchLog).filter_by(user_id=user.id).first():
        return True
    return False


def onboarding_options(db: Session) -> schemas.OnboardingOptionsOut:
    return schemas.OnboardingOptionsOut(
        title="บอกความต้องการของคุณ",
        subtitle="เลือกความต้องการเบื้องต้น เพื่อให้ StaySense ช่วยค้นหาที่พักที่เหมาะกับคุณมากขึ้น",
        typeOptions=[schemas.AccommodationTypeOut.model_validate(t) for t in db.query(models.AccommodationType).all()],
        districtOptions=[schemas.DistrictOut.model_validate(d) for d in db.query(models.District).all()],
        amenityOptions=[schemas.AmenityOut.model_validate(a) for a in db.query(models.Amenity).all()],
        atmosphereOptions=schemas.ATMOSPHERE_OPTIONS,
        placeCategoryOptions=schemas.PLACE_CATEGORIES,
    )


def featured_accommodations(db: Session, *, limit: int = 6) -> list[models.Accommodation]:
    stmt = base_accommodation_query().where(models.Accommodation.is_featured.is_(True))
    stmt = apply_sort(stmt, "recommended").limit(limit)
    items = db.scalars(stmt).unique().all()
    if items:
        return list(items)
    # no admin picks yet — fall back to the same "recommended" ordering used
    # everywhere else, so the section is never empty, without claiming a
    # curation that hasn't actually happened
    stmt = apply_sort(base_accommodation_query(), "recommended").limit(limit)
    return list(db.scalars(stmt).unique().all())


def has_enough_popularity_data(db: Session) -> bool:
    since = date.today() - timedelta(days=POPULARITY_WINDOW_DAYS)
    rows = (
        db.query(models.AccommodationEvent.accommodation_id)
        .filter(models.AccommodationEvent.created_at >= since)
        .distinct()
        .all()
    )
    if len(rows) < POPULARITY_MIN_ACCOMMODATIONS:
        return False
    total = (
        db.query(func.count(models.AccommodationEvent.id))
        .filter(models.AccommodationEvent.created_at >= since)
        .scalar()
        or 0
    )
    return total >= POPULARITY_MIN_EVENTS


def popular_accommodations(db: Session, *, limit: int = 6) -> list[tuple[models.Accommodation, str]]:
    """Top accommodations by real engagement in the last POPULARITY_WINDOW_DAYS
    days, weighted per POPULARITY_WEIGHTS. Returns (accommodation, statLabel)
    pairs — statLabel names the single most-telling real count for that item."""
    since = date.today() - timedelta(days=POPULARITY_WINDOW_DAYS)
    rows = (
        db.query(
            models.AccommodationEvent.accommodation_id,
            models.AccommodationEvent.event_type,
            func.count(models.AccommodationEvent.id).label("cnt"),
        )
        .filter(models.AccommodationEvent.created_at >= since)
        .group_by(models.AccommodationEvent.accommodation_id, models.AccommodationEvent.event_type)
        .all()
    )
    per_acc: dict[int, dict[str, int]] = {}
    for acc_id, event_type, cnt in rows:
        per_acc.setdefault(acc_id, {})[event_type] = cnt

    scored = []
    for acc_id, counts in per_acc.items():
        score = sum(counts.get(t, 0) * w for t, w in POPULARITY_WEIGHTS.items())
        if score > 0:
            scored.append((acc_id, score, counts))
    scored.sort(key=lambda row: -row[1])
    scored = scored[:limit]

    acc_ids = [acc_id for acc_id, _, _ in scored]
    if not acc_ids:
        return []
    accs = db.scalars(
        base_accommodation_query().where(models.Accommodation.id.in_(acc_ids))
    ).unique().all()
    accs_by_id = {a.id: a for a in accs}

    result = []
    for acc_id, _, counts in scored:
        acc = accs_by_id.get(acc_id)
        if not acc:
            continue
        best_type = max(counts, key=lambda t: counts[t] * POPULARITY_WEIGHTS.get(t, 0))
        stat_label = f"{EVENT_LABELS[best_type]} {counts[best_type]} ครั้งในช่วง {POPULARITY_WINDOW_DAYS} วันที่ผ่านมา"
        result.append((acc, stat_label))
    return result


def recently_viewed_accommodations(db: Session, user_id: int, *, limit: int = 6) -> list[models.Accommodation]:
    rows = (
        db.query(models.AccommodationEvent.accommodation_id, func.max(models.AccommodationEvent.created_at).label("last_seen"))
        .filter(models.AccommodationEvent.user_id == user_id, models.AccommodationEvent.event_type == "view")
        .group_by(models.AccommodationEvent.accommodation_id)
        .order_by(func.max(models.AccommodationEvent.created_at).desc())
        .limit(limit)
        .all()
    )
    ids_in_order = [acc_id for acc_id, _ in rows]
    if not ids_in_order:
        return []
    accs = {
        a.id: a
        for a in db.scalars(
            base_accommodation_query().where(models.Accommodation.id.in_(ids_in_order))
        ).unique().all()
    }
    return [accs[i] for i in ids_in_order if i in accs]


def atmosphere_match(acc: models.Accommodation, code: str) -> bool:
    keywords = ATMOSPHERE_KEYWORDS.get(code, [])
    haystack = " ".join([acc.description or "", *(acc.tags_json or []), acc.recommended_reason or ""])
    return any(kw in haystack for kw in keywords)


# --------------------------------------------------------- image management
# accommodation_images and room_type_images are managed identically apart
# from which column/model they key off of — these helpers are written once
# and parameterized by (model, owner_column) rather than duplicated per group,
# but the two groups are NEVER queried together (see app/routers/images.py).

def next_display_order(db: Session, model_cls, owner_attr, owner_id: int) -> int:
    current_max = (
        db.query(func.max(model_cls.sort_order))
        .filter(owner_attr == owner_id)
        .scalar()
    )
    return (current_max or -1) + 1


def ensure_group_has_cover(db: Session, model_cls, owner_attr, owner_id: int) -> None:
    """Invariant: if a group has at least one image and none is marked
    cover, promote the lowest-display_order one (preferring a published row
    so the public gallery always has a cover to show).

    The session is created with autoflush=False (see database.py), so a
    pending in-memory change to is_cover (e.g. the caller just hid the old
    cover) would NOT be visible to the query below without this explicit
    flush — without it, this function would see the stale pre-change state
    and wrongly conclude a cover already exists."""
    db.flush()
    existing_cover = (
        db.query(model_cls.id).filter(owner_attr == owner_id, model_cls.is_cover.is_(True)).first()
    )
    if existing_cover:
        return
    candidate = (
        db.query(model_cls)
        .filter(owner_attr == owner_id)
        .order_by((model_cls.status != "published"), model_cls.sort_order.asc())
        .first()
    )
    if candidate:
        candidate.is_cover = True


def set_cover(db: Session, model_cls, owner_attr, owner_id: int, image_id: int) -> None:
    """Single-transaction cover swap: clears every other row's is_cover in
    the same group, then sets the target — guarantees at most one cover per
    accommodation/room type even under repeated rapid clicks."""
    db.query(model_cls).filter(owner_attr == owner_id, model_cls.id != image_id).update({"is_cover": False})
    img = db.get(model_cls, image_id)
    img.is_cover = True
    db.commit()
    db.refresh(img)


def soft_delete_image(db: Session, model_cls, owner_attr, owner_id: int, image_id: int) -> None:
    """'Delete' hides the row (status='hidden') rather than removing it, so
    it can still be audited/recovered — see spec §12. If it was the cover,
    reassigns a new one from what's left."""
    img = db.get(model_cls, image_id)
    img.status = "hidden"
    img.is_cover = False
    ensure_group_has_cover(db, model_cls, owner_attr, owner_id)
    db.commit()


def reorder_images(db: Session, model_cls, owner_attr, owner_id: int, ordered_ids: list[int]) -> None:
    rows = {r.id: r for r in db.query(model_cls).filter(owner_attr == owner_id).all()}
    # ignore ids that don't belong to this owner — never let a client move an
    # image into (or reorder within) a gallery it doesn't belong to
    valid_ids = [i for i in ordered_ids if i in rows]
    for order, image_id in enumerate(valid_ids):
        rows[image_id].sort_order = order
    db.commit()


def log_image_audit(
    db: Session,
    *,
    admin_user_id: int | None,
    action: str,
    image_group: str,
    accommodation_id: int | None = None,
    room_type_id: int | None = None,
    image_id: int,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    db.add(
        models.ImageAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            image_group=image_group,
            accommodation_id=accommodation_id,
            room_type_id=room_type_id,
            image_id=image_id,
            old_value=old_value,
            new_value=new_value,
        )
    )
    db.commit()
