from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from .. import crud, match_reasons, models, query_intent, schemas
from ..auth import get_current_user, get_current_user_optional
from ..database import get_db
from ..semantic import index as search_index

router = APIRouter(prefix="/api/search", tags=["search"])

SIMILARITY_THRESHOLD = 0.15  # tune against real data; cosine similarity is 0..1
NEARBY_RADIUS_STEPS_KM = [5, 10, 25, 50]
NEARBY_MIN_RESULTS = 3
NOT_FOUND_OPTIONS = ["เลือกชื่อวัด", "เลือกอำเภอ", "ขยายรัศมี", "ล้างตัวกรอง", "ดูที่พักอื่น"]


def _type_labels(db: Session) -> dict[str, str]:
    return {t.code: t.name_th for t in db.query(models.AccommodationType).all()}


def _poi_labels(db: Session) -> dict[str, str]:
    # bare-noun overrides (match_reasons.CATEGORY_NOUN) read better in
    # reason/interpreted-query text than PLACE_CATEGORIES' compound admin
    # labels (e.g. "วัด" instead of "วัด/ศาสนสถาน").
    labels = {c["key"]: c["label"] for c in schemas.PLACE_CATEGORIES}
    labels.update(match_reasons.CATEGORY_NOUN)
    return labels


def _detected_filter_chips(
    intent: query_intent.ParsedIntent, *, type_labels: dict[str, str], amenity_labels: dict[str, str], poi_labels: dict[str, str],
) -> list[str]:
    chips = []
    if intent.accommodation_type_code:
        chips.append(type_labels.get(intent.accommodation_type_code, intent.accommodation_type_code))
    if intent.poi_name:
        chips.append(f"ใกล้{intent.poi_name}")
    elif intent.poi_category:
        chips.append(f"ใกล้{poi_labels.get(intent.poi_category, intent.poi_category)}")
    elif intent.use_current_location:
        chips.append("ใกล้ฉัน")
    if intent.district_name:
        chips.append(intent.district_name)
    if intent.guest_count:
        chips.append(f"สำหรับ {intent.guest_count} คน")
    for code in intent.facility_codes:
        chips.append(f"มี{amenity_labels.get(code, code)}")
    if intent.price_max is not None:
        chips.append(f"ราคาไม่เกิน {int(intent.price_max):,} บาท")
    return chips


def _corrections_out(corrections) -> list[schemas.TermCorrectionOut]:
    return [schemas.TermCorrectionOut(original=c.original, canonical=c.canonical) for c in corrections]


@router.get("/suggestions", response_model=schemas.SearchSuggestionsOut)
def suggestions(q: str, db: Session = Depends(get_db)):
    """Typing suggestions — never writes to search_logs (spec §3/§16: only a
    real submit counts as a search)."""
    norm = query_intent.normalize_query(db, q)
    intent = query_intent.parse_intent(db, norm.normalized)
    type_labels = _type_labels(db)
    poi_labels = _poi_labels(db)

    interpreted = query_intent.build_interpreted_as(intent, type_labels, poi_labels)

    type_label = type_labels.get(intent.accommodation_type_code, "ที่พัก") if intent.accommodation_type_code else "ที่พัก"
    query_suggestions = []
    if intent.district_name:
        query_suggestions.append(f"{type_label}ในอำเภอ{intent.district_name}")
    query_suggestions.append(f"{type_label}ใกล้ฉัน")
    if intent.poi_category or intent.poi_name:
        poi_label = intent.poi_name or poi_labels.get(intent.poi_category, intent.poi_category)
        query_suggestions.append(f"{type_label}ใกล้{poi_label}")
    else:
        query_suggestions.append(f"{type_label}ใกล้วัด")
    if intent.price_max is not None:
        query_suggestions.append(f"{type_label}ราคาไม่เกิน {int(intent.price_max):,} บาท")
    query_suggestions = list(dict.fromkeys(query_suggestions))[:4]  # dedupe, cap

    all_places = db.query(models.Place).all() if len(norm.normalized.strip()) >= 2 else []

    poi_suggestions = []
    if len(norm.normalized.strip()) >= 2:
        if intent.poi_category:
            # the user named a category ("ใกล้วัด") — surface real places in
            # that category, not a literal text match against "ใกล้วัด".
            poi_suggestions = [
                schemas.PoiSuggestionOut(name=p.name, category=p.category)
                for p in all_places if p.category == intent.poi_category
            ][:5]
        else:
            poi_suggestions = [
                schemas.PoiSuggestionOut(name=p.name, category=p.category)
                for p in all_places if norm.normalized in p.name or p.name in norm.normalized
            ][:5]

    acc_suggestions = []
    if len(norm.normalized.strip()) >= 2:
        hits = search_index.semantic_search(norm.normalized, top_k=8)
        if hits:
            accs = (
                db.query(models.Accommodation)
                .options(joinedload(models.Accommodation.district), joinedload(models.Accommodation.type))
                .filter(models.Accommodation.id.in_([h[0] for h in hits]))
                .filter(models.Accommodation.status == "published")
                .all()
            )
            by_id = {a.id: a for a in accs}
            for acc_id, _ in hits:
                acc = by_id.get(acc_id)
                if not acc:
                    continue
                if intent.accommodation_type_code and acc.type.code != intent.accommodation_type_code:
                    continue
                matched_poi_name, distance_km = None, None
                found = match_reasons.nearest_named_poi(db, acc, intent)
                if found:
                    matched_poi_name, distance_km = found[0].name, found[1]
                acc_suggestions.append(schemas.AccommodationSuggestionOut(
                    id=acc.id, name=acc.name, type=acc.type.name_th, district=acc.district.name,
                    matchedPoiName=matched_poi_name, distanceKm=distance_km,
                ))
        acc_suggestions = acc_suggestions[:8]

    return schemas.SearchSuggestionsOut(
        originalQuery=q,
        normalizedQuery=norm.normalized,
        interpretedAs=interpreted,
        querySuggestions=query_suggestions,
        poiSuggestions=poi_suggestions,
        accommodationSuggestions=acc_suggestions,
    )


@router.post("", response_model=schemas.SearchResponse)
def search(
    payload: schemas.SearchRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user_optional),
):
    norm = query_intent.normalize_query(db, payload.query, skip_correction=payload.raw)
    intent = query_intent.parse_intent(db, norm.normalized)
    type_labels = _type_labels(db)
    amenity_labels = {a.code: a.label_th for a in db.query(models.Amenity).all()}
    poi_labels = _poi_labels(db)

    # explicit UI filters always win over anything detected from free text
    type_code = payload.type or intent.accommodation_type_code
    district_names = payload.district or ([intent.district_name] if intent.district_name else [])
    price_max = payload.price_max if payload.price_max is not None else intent.price_max
    amenity_codes = sorted(set(payload.amenities) | set(intent.facility_codes))
    guest_count = payload.guest_count or intent.guest_count
    smoking = payload.smoking if payload.smoking is not None else intent.smoking
    extra_bed = payload.extra_bed or intent.extra_bed

    raw_results = search_index.semantic_search(norm.normalized, top_k=200)
    scored: dict[int, float] = {acc_id: sim for acc_id, sim in raw_results}

    interpreted = query_intent.build_interpreted_as(intent, type_labels, poi_labels)
    detected_filters = _detected_filter_chips(intent, type_labels=type_labels, amenity_labels=amenity_labels, poi_labels=poi_labels)

    def _log(result_count: int, district_id: int | None):
        crud.log_search(
            db, user_id=user.id if user else None, query_text=payload.query,
            price_ceiling=price_max, district_id=district_id, result_count=result_count,
            normalized_query=norm.normalized, detected_intent=intent.as_dict(), confidence=norm.confidence,
            save_history=not (user and not user.save_search_history),
        )

    def _meta(**extra) -> schemas.SearchMeta:
        return schemas.SearchMeta(
            priceCeiling=price_max, terms=[], originalQuery=payload.query, normalizedQuery=norm.normalized,
            interpretedAs=interpreted, detectedFilters=detected_filters, confidence=norm.confidence,
            corrections=_corrections_out(norm.corrections), **extra,
        )

    if not scored:
        _log(0, None)
        return schemas.SearchResponse(items=[], total=0, page=payload.page, pageSize=payload.page_size, meta=_meta())

    q = (
        db.query(models.Accommodation)
        .options(
            joinedload(models.Accommodation.district), joinedload(models.Accommodation.type),
            joinedload(models.Accommodation.amenities), joinedload(models.Accommodation.images),
        )
        .filter(models.Accommodation.id.in_(scored.keys()))
        .filter(models.Accommodation.status == "published")
    )
    q = crud.apply_filters(
        q, type_code=type_code, district_names=district_names or None,
        price_min=payload.price_min, price_max=price_max, rating_min=payload.rating_min,
        amenity_codes=amenity_codes or None, distance_max_km=payload.distance_max_km,
        guest_count=guest_count, smoking=smoking, extra_bed=extra_bed,
    )
    accs = q.all()

    # when the query names a POI/category, pull each candidate's own nearest
    # real distance up front so it can pull weight in the ranking too — not
    # just show up in the reason text (otherwise a hotel 60km from the named
    # temple can outrank one 500m away purely on text-similarity noise).
    wants_poi = bool(intent.poi_id or intent.poi_category)
    poi_distance: dict[int, float] = {}
    if wants_poi:
        for acc in accs:
            found = match_reasons.nearest_named_poi(db, acc, intent)
            if found:
                poi_distance[acc.id] = found[1]

    ranked = []
    for acc in accs:
        score = scored.get(acc.id, 0.0)
        if price_max is not None:
            score += 0.15 if float(acc.price_per_night) <= price_max else -0.3
        if wants_poi:
            d = poi_distance.get(acc.id)
            score += _distance_score(d, 20.0) * 0.3 if d is not None else -0.1
        if score >= SIMILARITY_THRESHOLD:
            ranked.append((score, acc))

    # build structured reasons once, up front, so we can tell whether the
    # nearby-POI promise (if any) was actually honored for anyone
    reasoned: list[tuple[float, models.Accommodation, match_reasons.ReasonSet]] = []
    for score, acc in ranked:
        rs = match_reasons.build_reasons(db, acc, intent, amenity_labels=amenity_labels, poi_labels=poi_labels)
        reasoned.append((score, acc, rs))

    # a full match ("ตรงกับความต้องการมาก") must always outrank a partial one
    # ("ตรงบางส่วน") regardless of raw semantic score — otherwise the badge
    # shown on a card can contradict its position in the results list.
    MATCH_LEVEL_PRIORITY = {"ตรงกับความต้องการมาก": 0, "ตรงบางส่วน": 1}
    reasoned.sort(key=lambda t: (MATCH_LEVEL_PRIORITY.get(t[2].match_level, 2), -t[0], -float(t[1].rating_avg)))

    if wants_poi and reasoned and not any(r.type == "poi_match" for _, _, rs in reasoned for r in rs.reasons):
        # detected a real POI/category ask but couldn't verify proximity for
        # ANY candidate — never present them as if they matched (spec §15)
        other = reasoned[:6]
        fav_ids = crud.user_favorite_ids(db, user)
        other_items = crud.apply_fav_flags([crud.to_accommodation_out(a) for _, a, _ in other], fav_ids)
        _log(0, None)
        target_label = intent.poi_name or poi_labels.get(intent.poi_category, intent.poi_category)
        pick_options = [f"เลือกชื่อ{target_label}"] + NOT_FOUND_OPTIONS[1:]
        return schemas.SearchResponse(
            items=[], total=0, page=payload.page, pageSize=payload.page_size,
            meta=_meta(
                notFoundMessage=f"ยังไม่พบที่พักที่มีข้อมูลว่าอยู่ใกล้{target_label}ตามเงื่อนไขนี้ กรุณาเลือกชื่อ{target_label} อำเภอ หรือขยายระยะทาง",
                notFoundOptions=pick_options,
            ),
            otherSuggestions=other_items,
        )

    total = len(reasoned)
    start = (payload.page - 1) * payload.page_size
    page_slice = reasoned[start:start + payload.page_size]

    district_id = None
    if len(district_names) == 1:
        district_row = db.query(models.District).filter_by(name=district_names[0]).first()
        district_id = district_row.id if district_row else None
    _log(total, district_id)

    fav_ids = crud.user_favorite_ids(db, user)
    items = []
    for _, acc, rs in page_slice:
        out = crud.to_accommodation_out(acc)
        out.matchReasons = [schemas.MatchReasonOut(type=r.type, message=r.message) for r in rs.reasons]
        out.matchedCriteria = rs.matched_criteria
        out.unmatchedCriteria = rs.unmatched_criteria
        out.matchLevel = rs.match_level
        out.matchedPois = [
            schemas.MatchedPoiOut(poiId=p.poi_id, name=p.name, category=p.category, distanceKm=p.distance_km, isRoad=p.is_road, mapUrl=p.map_url)
            for p in rs.matched_pois
        ]
        items.append(out)
    items = crud.apply_fav_flags(items, fav_ids)

    return schemas.SearchResponse(
        items=items, total=total, page=payload.page, pageSize=payload.page_size, meta=_meta(),
    )


def _distance_score(distance_km: float, radius_km: float) -> float:
    if radius_km <= 0:
        return 0.0
    return max(0.0, 1.0 - (distance_km / radius_km))


@router.post("/nearby", response_model=schemas.NearbySearchResponse)
def search_nearby(
    payload: schemas.NearbySearchRequest,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user_optional),
):
    amenities = db.query(models.Amenity).all()
    amenity_labels = {a.code: a.label_th for a in amenities}
    types_by_code = {t.code: t for t in db.query(models.AccommodationType).all()}
    type_labels = {code: t.name_th for code, t in types_by_code.items()}
    poi_labels = _poi_labels(db)

    norm = query_intent.normalize_query(db, payload.query, skip_correction=payload.raw)
    intent = query_intent.parse_intent(db, norm.normalized)
    intent.use_current_location = True  # this endpoint is always "near me"

    # explicit UI filter always wins over anything detected from free text
    type_code = payload.accommodation_type or intent.accommodation_type_code
    facility_codes = sorted(set(payload.facilities) | set(intent.facility_codes))
    price_max = payload.price_max if payload.price_max is not None else intent.price_max
    guest_count = payload.guest_count or intent.guest_count

    has_query_text = bool(payload.query.strip())
    requested_radius = max(1.0, payload.radius_km or 10.0)

    base = (
        crud.base_accommodation_query()
        .where(models.Accommodation.latitude.isnot(None))
        .where(models.Accommodation.longitude.isnot(None))
    )
    base = crud.apply_filters(
        base, type_code=type_code, district_names=payload.district or None,
        price_min=payload.price_min, price_max=price_max, rating_min=payload.rating_min,
        amenity_codes=facility_codes or None, guest_count=guest_count,
    )
    candidates = db.scalars(base).unique().all()

    with_distance = [(acc, crud.haversine_km(payload.latitude, payload.longitude, acc.latitude, acc.longitude)) for acc in candidates]

    steps = [r for r in NEARBY_RADIUS_STEPS_KM if r >= requested_radius] or [requested_radius]
    if requested_radius not in steps:
        steps = [requested_radius] + steps
    radius_used = requested_radius
    in_radius = [pair for pair in with_distance if pair[1] <= radius_used]
    expanded = False
    for step in steps:
        if step <= radius_used:
            continue
        if len(in_radius) >= NEARBY_MIN_RESULTS:
            break
        radius_used = step
        in_radius = [pair for pair in with_distance if pair[1] <= radius_used]
        expanded = True

    radius_message = None
    if expanded:
        radius_message = (
            f"พบที่พักในระยะ {requested_radius:g} กิโลเมตรน้อยเกินไป "
            f"ระบบจึงขยายพื้นที่ค้นหาเป็น {radius_used:g} กิโลเมตร"
        )

    pure_location_only = not has_query_text
    force_distance_sort = payload.sort_by == "distance" or pure_location_only
    use_relevance = not force_distance_sort

    semantic_scores: dict[int, float] = {}
    if use_relevance and has_query_text:
        semantic_scores = dict(search_index.semantic_search(norm.normalized, top_k=200))

    requested_filter_count = sum([1 if type_code else 0, 1 if price_max is not None else 0, len(facility_codes)]) or 0

    scored = []
    for acc, distance_km in in_radius:
        matched_filters = 0
        if type_code and acc.type.code == type_code:
            matched_filters += 1
        if price_max is not None and float(acc.price_per_night) <= price_max:
            matched_filters += 1
        acc_amenity_codes = {a.code for a in acc.amenities}
        matched_facilities = [c for c in facility_codes if c in acc_amenity_codes]
        matched_filters += len(matched_facilities)
        filter_score = (matched_filters / requested_filter_count) if requested_filter_count else 0.0
        sem_score = semantic_scores.get(acc.id, 0.0)
        dist_score = _distance_score(distance_km, radius_used)
        final_score = sem_score * 0.5 + filter_score * 0.3 + dist_score * 0.2
        scored.append((acc, distance_km, final_score))

    if force_distance_sort:
        scored.sort(key=lambda t: t[1])
    elif payload.sort_by == "price-asc":
        scored.sort(key=lambda t: float(t[0].price_per_night))
    else:
        scored.sort(key=lambda t: (-t[2], t[1]))

    total = len(scored)
    start = (payload.page - 1) * payload.page_size
    page_slice = scored[start:start + payload.page_size]

    fav_ids = crud.user_favorite_ids(db, user)
    items = []
    for i, (acc, distance_km, final_score) in enumerate(page_slice):
        out = crud.to_accommodation_out(acc)
        out.distanceFromUserKm = round(distance_km, 2)
        rs = match_reasons.build_reasons(
            db, acc, intent, distance_km=distance_km, distance_is_road=False,
            amenity_labels=amenity_labels, poi_labels=poi_labels,
        )
        out.matchReasons = [schemas.MatchReasonOut(type=r.type, message=r.message) for r in rs.reasons]
        out.matchedCriteria = rs.matched_criteria
        out.unmatchedCriteria = rs.unmatched_criteria
        out.matchedPois = [
            schemas.MatchedPoiOut(poiId=p.poi_id, name=p.name, category=p.category, distanceKm=p.distance_km, isRoad=p.is_road, mapUrl=p.map_url)
            for p in rs.matched_pois
        ]

        if rs.match_level:
            out.matchLevel = rs.match_level
        elif use_relevance:
            start_idx = start + i
            out.matchLevel = (
                "ตรงกับความต้องการมาก" if start_idx == 0
                else "ตรงกับความต้องการ" if start_idx < 3
                else "ตรงบางส่วน"
            )
        items.append(out)
    items = crud.apply_fav_flags(items, fav_ids)

    type_name = types_by_code[type_code].name_th if type_code else None
    title = f"{type_name}ใกล้คุณ" if type_name else "ที่พักใกล้คุณ"
    if facility_codes:
        title += "ที่มี" + "และ".join(amenity_labels.get(c, c) for c in facility_codes[:2])
    subtitle = f"พบ {total:,} แห่งภายในระยะ {radius_used:g} กิโลเมตรจากตำแหน่งปัจจุบันของคุณ"

    crud.log_search(
        db, user_id=user.id if user else None, query_text=payload.query,
        price_ceiling=price_max, district_id=None, result_count=total,
        accommodation_type=type_code, facilities=facility_codes or None,
        radius_km=radius_used, sort_by=payload.sort_by, use_current_location=True,
        normalized_query=norm.normalized, detected_intent=intent.as_dict(), confidence=norm.confidence,
        save_history=not (user and not user.save_search_history),
    )

    return schemas.NearbySearchResponse(
        title=title, subtitle=subtitle, query=payload.query,
        detectedIntent=schemas.DetectedIntentOut(
            useCurrentLocation=True, accommodationType=intent.accommodation_type_code,
            facilities=intent.facility_codes, priceMax=intent.price_max,
        ),
        radiusKm=radius_used, requestedRadiusKm=requested_radius,
        radiusExpanded=expanded, radiusExpandedMessage=radius_message,
        accommodationType=type_code, facilities=facility_codes, priceMax=price_max,
        district=payload.district, sortBy=payload.sort_by,
        total=total, resultCount=len(items), page=payload.page, pageSize=payload.page_size, items=items,
        normalizedQuery=norm.normalized,
        interpretedAs=query_intent.build_interpreted_as(intent, type_labels, poi_labels),
        detectedFilters=_detected_filter_chips(intent, type_labels=type_labels, amenity_labels=amenity_labels, poi_labels=poi_labels),
        confidence=norm.confidence, corrections=_corrections_out(norm.corrections),
    )


@router.post("/reindex", status_code=200)
def reindex(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.role != "admin":
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    count = search_index.build_index(db)
    return {"indexed": count}
