from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud, match_reasons, models, query_intent, schemas
from ..auth import get_current_user, get_current_user_optional
from ..database import get_db
from ..semantic import index as search_index
from .search import _detected_filter_chips, _distance_score, _poi_labels, _type_labels

router = APIRouter(prefix="/api", tags=["home"])

MATCH_SIMILARITY_THRESHOLD = 0.15
SECTION_LIMIT = 6


def _amenity_labels(db: Session) -> dict[str, str]:
    return {a.code: a.label_th for a in db.query(models.Amenity).all()}


def _highlight_text(acc: models.Accommodation, amenity_labels: dict[str, str]) -> str | None:
    """'จุดเด่น: ...' built only from this accommodation's own real amenities
    and tags — never invented copy."""
    parts = []
    top = [amenity_labels.get(a.code, a.code) for a in acc.amenities[:3]]
    if top:
        parts.append("มี" + " ".join(top))
    if acc.tags_json:
        parts.append(f"และ{acc.tags_json[0]}")
    return " ".join(parts) if parts else None


def _build_match_section(
    db: Session,
    fav_ids: set[int],
    *,
    norm: "query_intent.NormalizeResult",
    intent: "query_intent.ParsedIntent",
    type_code: str | None,
    district_names: list[str],
    price_min: float | None,
    price_max: float | None,
    amenity_codes: list[str],
    poi_labels: dict[str, str],
) -> schemas.HomeSectionOut | None:
    """Same query_intent/match_reasons pipeline as /api/search (spec §1/§8:
    every card gets its own real, itemized reasons — never a generic
    "ตรงกับคำค้นของคุณ" string) — the home page's inline search preview must
    not fall back to a cruder, unrelated implementation just because it
    lives on a different endpoint."""
    amenity_labels = _amenity_labels(db)
    has_query = bool(norm.normalized and norm.normalized.strip())

    if has_query:
        raw = search_index.semantic_search(norm.normalized.strip(), top_k=100)
        if not raw:
            return None
        scored_map = dict(raw)
        stmt = crud.base_accommodation_query().where(models.Accommodation.id.in_(scored_map.keys()))
        stmt = crud.apply_filters(
            stmt, type_code=type_code, district_names=district_names or None,
            price_min=price_min, price_max=price_max, amenity_codes=amenity_codes or None,
            guest_count=intent.guest_count, smoking=intent.smoking, extra_bed=intent.extra_bed,
        )
        accs = db.scalars(stmt).unique().all()

        # same real-distance ranking bonus as /api/search — a POI-driven
        # query shouldn't outrank by text-similarity noise alone (spec §15)
        wants_poi = bool(intent.poi_id or intent.poi_category)
        poi_distance: dict[int, float] = {}
        if wants_poi:
            for acc in accs:
                found = match_reasons.nearest_named_poi(db, acc, intent)
                if found:
                    poi_distance[acc.id] = found[1]

        ranked = []
        for acc in accs:
            score = scored_map.get(acc.id, 0.0)
            if price_max is not None:
                score += 0.15 if float(acc.price_per_night) <= price_max else -0.3
            if wants_poi:
                d = poi_distance.get(acc.id)
                score += _distance_score(d, 20.0) * 0.3 if d is not None else -0.1
            if score >= MATCH_SIMILARITY_THRESHOLD:
                ranked.append((score, acc))

        # build reasons up front so match-level completeness can drive
        # ranking, same fix as /api/search — a full match ("ตรงกับความต้องการมาก")
        # must outrank a partial one ("ตรงบางส่วน") regardless of raw semantic
        # score, otherwise a card's own badge can contradict its position.
        reasoned = []
        for score, acc in ranked:
            rs = match_reasons.build_reasons(db, acc, intent, amenity_labels=amenity_labels, poi_labels=poi_labels)
            reasoned.append((score, acc, rs))
        MATCH_LEVEL_PRIORITY = {"ตรงกับความต้องการมาก": 0, "ตรงบางส่วน": 1}
        reasoned.sort(key=lambda t: (MATCH_LEVEL_PRIORITY.get(t[2].match_level, 2), -t[0], -float(t[1].rating_avg)))
        reasoned = reasoned[:SECTION_LIMIT]
        if not reasoned:
            return None
        accs_ordered = [acc for _, acc, _ in reasoned]
        reasons_by_id = {acc.id: rs for _, acc, rs in reasoned}
    else:
        accs_ordered, _total = crud.list_accommodations(
            db, type_code=type_code, district_names=district_names or None,
            price_min=price_min, price_max=price_max, rating_min=None,
            amenity_codes=amenity_codes or None, distance_max_km=None,
            sort="recommended", page=1, page_size=SECTION_LIMIT,
        )
        if not accs_ordered:
            return None
        reasons_by_id = {}

    items = []
    for i, acc in enumerate(accs_ordered):
        out = crud.to_accommodation_out(acc)
        rs = reasons_by_id.get(acc.id) if has_query else None
        if rs:
            out.matchReasons = [schemas.MatchReasonOut(type=r.type, message=r.message) for r in rs.reasons]
            out.matchedCriteria = rs.matched_criteria
            out.unmatchedCriteria = rs.unmatched_criteria
            out.matchedPois = [
                schemas.MatchedPoiOut(poiId=p.poi_id, name=p.name, category=p.category, distanceKm=p.distance_km, isRoad=p.is_road, mapUrl=p.map_url)
                for p in rs.matched_pois
            ]
        out.matchLevel = (rs.match_level if rs else None) or (
            "ตรงกับความต้องการมาก" if i == 0 else ("ตรงกับความต้องการ" if i < 3 else "ตรงบางส่วน")
        )
        items.append(out)

    items = crud.apply_fav_flags(items, fav_ids)
    return schemas.HomeSectionOut(
        key="match",
        title="ที่พักที่ตรงกับการค้นหาของคุณ",
        subtitle="เรียงลำดับจากความสอดคล้องกับข้อความค้นหาและตัวกรองที่คุณเลือก",
        items=items,
    )


def _score_and_shape(
    db: Session, candidates: list[models.Accommodation], fav_ids: set[int], reason_fn, *, limit: int = SECTION_LIMIT
) -> list[schemas.AccommodationOut]:
    items = []
    for acc in candidates[:limit]:
        out = crud.to_accommodation_out(acc)
        out.matchReason = reason_fn(acc)
        items.append(out)
    return crud.apply_fav_flags(items, fav_ids)


def _build_personal_section(db: Session, user: models.User, fav_ids: set[int]) -> schemas.HomeSectionOut | None:
    amenity_labels = _amenity_labels(db)
    title = "ที่พักที่แนะนำสำหรับคุณ"
    subtitle = "คัดเลือกจากความต้องการและกิจกรรมที่คุณอนุญาตให้ StaySense นำมาใช้"

    pref = crud.get_user_preference(db, user.id)
    if pref:
        candidates = db.scalars(crud.base_accommodation_query()).unique().all()
        if pref.type_codes:
            candidates = [a for a in candidates if a.type.code in pref.type_codes]
        if pref.district_names:
            candidates = [a for a in candidates if a.district.name in pref.district_names]
        if pref.budget_min is not None:
            candidates = [a for a in candidates if float(a.price_per_night) >= float(pref.budget_min)]
        if pref.budget_max is not None:
            candidates = [a for a in candidates if float(a.price_per_night) <= float(pref.budget_max)]

        pref_amenities = set(pref.amenity_codes or [])
        pref_atmospheres = pref.atmosphere_codes or []

        def score(acc):
            overlap = len({a.code for a in acc.amenities} & pref_amenities)
            atmosphere_hits = sum(1 for code in pref_atmospheres if crud.atmosphere_match(acc, code))
            return overlap * 2 + atmosphere_hits * 2 + float(acc.rating_avg) * 0.1

        candidates.sort(key=lambda a: -score(a))
        if not candidates:
            return None

        def reason(acc):
            parts = []
            if pref.type_codes and acc.type.code in pref.type_codes:
                parts.append(f"คุณสนใจ{acc.type.name_th}")
            if pref.district_names and acc.district.name in pref.district_names:
                parts.append(f"อยู่ในอำเภอ{acc.district.name}ที่คุณต้องการ")
            if pref.budget_max is not None and float(acc.price_per_night) <= float(pref.budget_max):
                parts.append(f"งบไม่เกิน {int(pref.budget_max):,} บาท")
            matched = [amenity_labels.get(c, c) for c in pref_amenities if c in {a.code for a in acc.amenities}]
            if matched:
                parts.append("ต้องการ" + "และ".join(matched[:2]))
            return "แนะนำเพราะ" + " ".join(parts) if parts else "คัดเลือกจากความต้องการที่คุณระบุไว้"

        items = _score_and_shape(db, candidates, fav_ids, reason)
        if not items:
            return None
        return schemas.HomeSectionOut(key="personal", title=title, subtitle=subtitle, badge="สำหรับคุณ", items=items)

    # no explicit onboarding answers — derive an implicit profile from favorites
    fav_acc_ids = [f.accommodation_id for f in db.query(models.Favorite).filter_by(user_id=user.id).all()]
    if fav_acc_ids:
        fav_accs = db.scalars(select(models.Accommodation).where(models.Accommodation.id.in_(fav_acc_ids))).unique().all()
        district_counts = Counter(a.district.name for a in fav_accs)
        type_counts = Counter(a.type.code for a in fav_accs)
        amenity_pool = set()
        for a in fav_accs:
            amenity_pool |= {am.code for am in a.amenities}
        top_district = district_counts.most_common(1)[0][0] if district_counts else None
        top_type = type_counts.most_common(1)[0][0] if type_counts else None

        candidates = db.scalars(
            crud.base_accommodation_query().where(models.Accommodation.id.notin_(fav_acc_ids))
        ).unique().all()

        def score(acc):
            s = 0.0
            if top_district and acc.district.name == top_district:
                s += 3
            if top_type and acc.type.code == top_type:
                s += 2
            s += len({am.code for am in acc.amenities} & amenity_pool)
            return s

        scored = [(score(a), a) for a in candidates]
        scored = [pair for pair in scored if pair[0] > 0]
        scored.sort(key=lambda pair: -pair[0])
        if scored:
            items = _score_and_shape(
                db, [a for _, a in scored], fav_ids,
                lambda acc: "คล้ายกับที่พักที่คุณเคยบันทึกไว้",
            )
            if items:
                return schemas.HomeSectionOut(key="personal", title=title, subtitle=subtitle, badge="สำหรับคุณ", items=items)

    # still nothing explicit — fall back to search-history-derived signal, if allowed
    if user.allow_personalization:
        logs = (
            db.query(models.SearchLog)
            .filter_by(user_id=user.id)
            .order_by(models.SearchLog.created_at.desc())
            .limit(20)
            .all()
        )
        district_ids = [l.extracted_district_id for l in logs if l.extracted_district_id]
        if district_ids:
            top_district_id = Counter(district_ids).most_common(1)[0][0]
            candidates = db.scalars(
                crud.base_accommodation_query().where(models.Accommodation.district_id == top_district_id)
            ).unique().all()
            if candidates:
                items = _score_and_shape(
                    db, candidates, fav_ids,
                    lambda acc: "อยู่ใกล้สถานที่ที่คุณค้นหาบ่อย",
                )
                if items:
                    return schemas.HomeSectionOut(key="personal", title=title, subtitle=subtitle, badge="สำหรับคุณ", items=items)

    return None


def _build_featured_section(db: Session, fav_ids: set[int]) -> schemas.HomeSectionOut | None:
    accs = crud.featured_accommodations(db, limit=SECTION_LIMIT)
    if not accs:
        return None
    amenity_labels = _amenity_labels(db)
    items = _score_and_shape(db, accs, fav_ids, lambda acc: _highlight_text(acc, amenity_labels))
    return schemas.HomeSectionOut(
        key="featured",
        title="ที่พักน่าสนใจในพิษณุโลก",
        subtitle="สำรวจที่พักที่น่าสนใจจากพื้นที่และประเภทที่พักต่าง ๆ ในจังหวัดพิษณุโลก",
        badge="คัดเลือกโดย StaySense",
        items=items,
    )


def _build_popular_section(db: Session, fav_ids: set[int]) -> schemas.HomeSectionOut | None:
    pairs = crud.popular_accommodations(db, limit=SECTION_LIMIT)
    if not pairs:
        return None
    items = []
    for i, (acc, stat_label) in enumerate(pairs):
        out = crud.to_accommodation_out(acc)
        out.rank = i + 1
        out.statLabel = stat_label
        items.append(out)
    items = crud.apply_fav_flags(items, fav_ids)
    return schemas.HomeSectionOut(
        key="popular",
        title="ที่พักยอดนิยมในพิษณุโลก",
        subtitle="ที่พักที่ได้รับความสนใจจากผู้ใช้งานบน StaySense ในช่วงนี้",
        items=items,
    )


def _build_recently_viewed_section(db: Session, user: models.User, fav_ids: set[int]) -> schemas.HomeSectionOut | None:
    accs = crud.recently_viewed_accommodations(db, user.id, limit=SECTION_LIMIT)
    if not accs:
        return None
    items = crud.apply_fav_flags([crud.to_accommodation_out(a) for a in accs], fav_ids)
    return schemas.HomeSectionOut(
        key="recent",
        title="ที่พักที่คุณเปิดดูล่าสุด",
        subtitle="รายการที่พักที่คุณเพิ่งเข้าชม",
        items=items,
    )


@router.get("/home", response_model=schemas.HomeOut)
def get_home(
    q: str | None = None,
    type: str | None = None,
    district: list[str] = Query(default=[]),
    price_min: float | None = None,
    price_max: float | None = None,
    amenities: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user_optional),
):
    fav_ids = crud.user_favorite_ids(db, user)
    has_search = bool((q and q.strip()) or type or district or price_min is not None or price_max is not None or amenities)

    match_section = None
    search_meta = None
    if has_search:
        norm = query_intent.normalize_query(db, q or "")
        intent = query_intent.parse_intent(db, norm.normalized)
        poi_labels = _poi_labels(db)
        type_labels = _type_labels(db)

        # explicit filter controls always win over anything detected from free text
        type_code = type or intent.accommodation_type_code
        district_names = district or ([intent.district_name] if intent.district_name else [])
        price_max_merged = price_max if price_max is not None else intent.price_max
        amenity_codes = sorted(set(amenities) | set(intent.facility_codes))

        match_section = _build_match_section(
            db, fav_ids, norm=norm, intent=intent, type_code=type_code, district_names=district_names,
            price_min=price_min, price_max=price_max_merged, amenity_codes=amenity_codes, poi_labels=poi_labels,
        )

        if q and q.strip():
            amenity_labels = _amenity_labels(db)
            search_meta = schemas.SearchMeta(
                priceCeiling=price_max_merged, terms=[], originalQuery=q, normalizedQuery=norm.normalized,
                interpretedAs=query_intent.build_interpreted_as(intent, type_labels, poi_labels),
                detectedFilters=_detected_filter_chips(intent, type_labels=type_labels, amenity_labels=amenity_labels, poi_labels=poi_labels),
                confidence=norm.confidence, corrections=[schemas.TermCorrectionOut(original=c.original, canonical=c.canonical) for c in norm.corrections],
            )
            district_id = None
            if len(district_names) == 1:
                district_row = db.query(models.District).filter_by(name=district_names[0]).first()
                district_id = district_row.id if district_row else None
            crud.log_search(
                db, user_id=user.id if user else None, query_text=q,
                price_ceiling=price_max_merged, district_id=district_id,
                result_count=len(match_section.items) if match_section else 0,
                normalized_query=norm.normalized, detected_intent=intent.as_dict(), confidence=norm.confidence,
                save_history=not (user and not user.save_search_history),
            )

    onboarding = None
    personal_section = None
    if user:
        if crud.has_personal_data(db, user):
            personal_section = _build_personal_section(db, user, fav_ids)
        if not personal_section:
            onboarding = crud.onboarding_options(db)

    popular_section = None
    featured_section = None
    if crud.has_enough_popularity_data(db):
        popular_section = _build_popular_section(db, fav_ids)
    if not popular_section:
        featured_section = _build_featured_section(db, fav_ids)

    recently_viewed_section = None
    if user:
        recently_viewed_section = _build_recently_viewed_section(db, user, fav_ids)

    return schemas.HomeOut(
        matchSection=match_section,
        personalSection=personal_section,
        onboarding=onboarding,
        featuredSection=featured_section,
        popularSection=popular_section,
        recentlyViewedSection=recently_viewed_section,
        searchMeta=search_meta,
    )


@router.post("/accommodations/{accommodation_id}/events", status_code=204)
def log_accommodation_event(
    accommodation_id: int,
    payload: schemas.EventCreate,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_current_user_optional),
):
    if payload.event_type not in schemas.EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"event_type must be one of {sorted(schemas.EVENT_TYPES)}")
    acc = db.get(models.Accommodation, accommodation_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    crud.log_event(db, accommodation_id=accommodation_id, user_id=user.id if user else None, event_type=payload.event_type)


@router.get("/me/preferences", response_model=schemas.UserPreferenceOut | None)
def get_my_preferences(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    pref = crud.get_user_preference(db, user.id)
    if not pref:
        return None
    return schemas.UserPreferenceOut(
        type_codes=pref.type_codes or [], district_names=pref.district_names or [],
        budget_min=float(pref.budget_min) if pref.budget_min is not None else None,
        budget_max=float(pref.budget_max) if pref.budget_max is not None else None,
        guest_count=pref.guest_count, amenity_codes=pref.amenity_codes or [],
        atmosphere_codes=pref.atmosphere_codes or [], near_place_categories=pref.near_place_categories or [],
        updatedAt=pref.updated_at,
    )


@router.put("/me/preferences", response_model=schemas.UserPreferenceOut)
def put_my_preferences(
    payload: schemas.UserPreferenceIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    invalid_atmospheres = set(payload.atmosphere_codes) - schemas.VALID_ATMOSPHERE_CODES
    if invalid_atmospheres:
        raise HTTPException(status_code=400, detail=f"unknown atmosphere codes: {sorted(invalid_atmospheres)}")
    pref = crud.save_user_preference(db, user.id, payload)
    return schemas.UserPreferenceOut(
        type_codes=pref.type_codes or [], district_names=pref.district_names or [],
        budget_min=float(pref.budget_min) if pref.budget_min is not None else None,
        budget_max=float(pref.budget_max) if pref.budget_max is not None else None,
        guest_count=pref.guest_count, amenity_codes=pref.amenity_codes or [],
        atmosphere_codes=pref.atmosphere_codes or [], near_place_categories=pref.near_place_categories or [],
        updatedAt=pref.updated_at,
    )


@router.get("/me/personalization", response_model=schemas.PersonalizationSettingsOut)
def get_personalization_settings(user: models.User = Depends(get_current_user)):
    return schemas.PersonalizationSettingsOut(allowPersonalization=user.allow_personalization)


@router.put("/me/personalization", response_model=schemas.PersonalizationSettingsOut)
def set_personalization_settings(
    payload: schemas.PersonalizationSettingsIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    user.allow_personalization = payload.allow_personalization
    db.commit()
    return schemas.PersonalizationSettingsOut(allowPersonalization=user.allow_personalization)


@router.delete("/me/search-history", status_code=204)
def clear_my_search_history(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.query(models.SearchLog).filter_by(user_id=user.id).delete()
    db.commit()


@router.get("/me/search-history-setting", response_model=schemas.SearchHistorySettingOut)
def get_search_history_setting(user: models.User = Depends(get_current_user)):
    return schemas.SearchHistorySettingOut(saveSearchHistory=user.save_search_history)


@router.put("/me/search-history-setting", response_model=schemas.SearchHistorySettingOut)
def set_search_history_setting(
    payload: schemas.SearchHistorySettingIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    user.save_search_history = payload.save_search_history
    db.commit()
    return schemas.SearchHistorySettingOut(saveSearchHistory=user.save_search_history)
