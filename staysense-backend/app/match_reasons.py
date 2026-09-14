"""Structured, itemized match-reason generation shared by /api/search and
/api/search/nearby — replaces the old single flat matchReason string built
ad hoc inside routers/search.py. Every reason here is backed by real data
already loaded on the accommodation/room types; nothing is invented (spec
§7/§20: never claim a facility, price fit, or nearby POI the data doesn't
actually support)."""

from dataclasses import dataclass, field

from . import crud, models
from .query_intent import VIEW_LABELS, ParsedIntent

# priority order per spec §8: place/location > type > price > guest count >
# facility > view/atmosphere > special conditions
PRIORITY = {
    "poi_match": 0,
    "poi_match_more": 0,
    "poi_current_location": 0,
    "type_match": 1,
    "price_match": 2,
    "guest_count_match": 3,
    "facility_match": 4,
    "view_match": 5,
    "view_no_data": 5,
    "atmosphere_match": 5,
    "atmosphere_no_data": 5,
    "special_condition_match": 6,
}

# how close a place must be to count as "ใกล้" for its own category (spec
# §17) — never used to fabricate a number, only to decide whether a real,
# resolved distance is close enough to lead the reason list with.
POI_DISTANCE_THRESHOLDS_KM = {
    "convenience": 3.0, "restaurant": 3.0, "nightlife": 3.0,
    "temple": 5.0, "mall": 5.0, "hospital": 5.0, "station": 5.0, "market": 5.0,
    "attraction": 10.0, "museum": 10.0, "university": 10.0, "airport": 10.0,
}
DEFAULT_POI_THRESHOLD_KM = 5.0

# short bare-noun override for categories whose PLACE_CATEGORIES label is a
# compound like "วัด/ศาสนสถาน" — the overflow line ("และวัดใกล้เคียงอีก 2
# แห่ง") reads better with the plain noun.
CATEGORY_NOUN = {"temple": "วัด"}

ATMOSPHERE_LABELS = {"quiet": "เงียบสงบ", "nature": "ใกล้ชิดธรรมชาติ", "city": "อยู่ใจกลางเมือง"}

MAX_POI_REASONS_ON_CARD = 3


@dataclass
class MatchReason:
    type: str
    message: str


@dataclass
class MatchedPoi:
    poi_id: int
    name: str
    category: str
    distance_km: float
    is_road: bool
    map_url: str | None


@dataclass
class ReasonSet:
    reasons: list[MatchReason] = field(default_factory=list)
    matched_pois: list[MatchedPoi] = field(default_factory=list)
    matched_criteria: list[str] = field(default_factory=list)
    unmatched_criteria: list[str] = field(default_factory=list)
    match_level: str | None = None


def _threshold_for(category: str | None) -> float:
    return POI_DISTANCE_THRESHOLDS_KM.get(category, DEFAULT_POI_THRESHOLD_KM)


def _map_url(place: "models.Place") -> str | None:
    if place.latitude is None or place.longitude is None:
        return None
    return f"https://www.google.com/maps/dir/?api=1&destination={place.latitude},{place.longitude}"


def nearby_pois(db, acc: models.Accommodation, category: str, *, limit: int = 8) -> list[MatchedPoi]:
    """Every real place in `category` within that category's "ใกล้" distance
    threshold (spec §17) for this specific accommodation, nearest first.
    Only places with a resolvable curated/haversine distance are considered
    — never a fabricated place or number (spec §15/§18)."""
    threshold = _threshold_for(category)
    found: list[MatchedPoi] = []
    for p in db.query(models.Place).filter(models.Place.category == category).all():
        resolved = crud.resolve_place_distance(db, acc, p)
        if resolved is None:
            continue
        d_km, is_road = resolved
        if d_km <= threshold:
            found.append(MatchedPoi(p.id, p.name, p.category, d_km, is_road, _map_url(p)))
    found.sort(key=lambda mp: mp.distance_km)
    return found[:limit]


def nearest_named_poi(db, acc: models.Accommodation, intent: ParsedIntent) -> tuple["models.Place", float, bool] | None:
    """Single-nearest-match helper for callers that only need one distance
    number (routers/search.py's ranking bonus, the suggestions endpoint's
    dropdown rows) — build_reasons() below uses the richer nearby_pois()/
    specific-place lookup so a card can list more than one real POI."""
    if intent.poi_id:
        place = db.get(models.Place, intent.poi_id)
        resolved = crud.resolve_place_distance(db, acc, place) if place else None
        return (place, resolved[0], resolved[1]) if place and resolved else None
    if intent.poi_category:
        pois = nearby_pois(db, acc, intent.poi_category, limit=1)
        if pois:
            p = pois[0]
            return db.get(models.Place, p.poi_id), p.distance_km, p.is_road
    return None


def build_reasons(
    db,
    acc: models.Accommodation,
    intent: ParsedIntent,
    *,
    distance_km: float | None = None,
    distance_is_road: bool = False,
    amenity_labels: dict[str, str] | None = None,
    poi_labels: dict[str, str] | None = None,
) -> ReasonSet:
    """`distance_km`/`distance_is_road` let callers who already computed a
    live "near me" distance (routers/search.py's /nearby handler) pass it
    straight through instead of re-querying; otherwise a named POI/category
    is resolved against real accommodation_places/haversine data here.

    Only POI, view, and atmosphere criteria can end up in
    `unmatched_criteria` — type/price/guest-count/facility are already
    enforced as hard SQL filters upstream (crud.apply_filters), so every
    candidate reaching this function already satisfies them by construction.
    """
    amenity_labels = amenity_labels or {}
    poi_labels = poi_labels or {}
    reasons: list[MatchReason] = []
    matched_pois: list[MatchedPoi] = []
    matched: list[str] = []
    unmatched: list[str] = []

    # --- POI / location -----------------------------------------------
    if intent.use_current_location and distance_km is not None:
        reasons.append(MatchReason(
            "poi_current_location",
            f"อยู่ห่างจากตำแหน่งปัจจุบันของคุณประมาณ {crud.format_distance_th(distance_km, is_road=distance_is_road)}",
        ))
        matched.append("current_location")
    elif intent.poi_id:
        # a specific place was named ("ใกล้วัดนางพญา") — show only that one
        # as the primary reason, never blended with other places in its
        # category (spec §4).
        place = db.get(models.Place, intent.poi_id)
        resolved = crud.resolve_place_distance(db, acc, place) if place else None
        if place and resolved:
            d_km, is_road = resolved
            reasons.append(MatchReason(
                "poi_match", f"อยู่ห่างจาก{place.name}ประมาณ {crud.format_distance_th(d_km, is_road=is_road)}",
            ))
            matched_pois.append(MatchedPoi(place.id, place.name, place.category, d_km, is_road, _map_url(place)))
            matched.append("poi")
        else:
            unmatched.append("poi")
    elif intent.poi_category:
        # no specific name — surface every real place in the category that's
        # actually within "ใกล้" range, nearest first (spec §2/§3).
        pois = nearby_pois(db, acc, intent.poi_category, limit=8)
        if pois:
            for p in pois[:MAX_POI_REASONS_ON_CARD]:
                reasons.append(MatchReason("poi_match", f"ใกล้{p.name}ประมาณ {crud.format_distance_th(p.distance_km, is_road=p.is_road)}"))
            if len(pois) > MAX_POI_REASONS_ON_CARD:
                noun = CATEGORY_NOUN.get(intent.poi_category, poi_labels.get(intent.poi_category, "สถานที่"))
                reasons.append(MatchReason("poi_match_more", f"และ{noun}ใกล้เคียงอีก {len(pois) - MAX_POI_REASONS_ON_CARD} แห่ง"))
            matched_pois.extend(pois)
            matched.append("poi")
        else:
            # no place in this category is within the "ใกล้" threshold (or
            # has any resolvable distance at all) for this accommodation —
            # never claim proximity; the router's not-found gate handles the
            # case where NO candidate has this data (spec §15/§18).
            unmatched.append("poi")

    # --- accommodation type (already SQL-filtered when set — always true) --
    if intent.accommodation_type_code and acc.type.code == intent.accommodation_type_code:
        reasons.append(MatchReason("type_match", f"เป็น{acc.type.name_th}ตามประเภทที่ค้นหา"))
        matched.append("type")

    # --- price (already SQL-filtered when set — always true) --------------
    if intent.price_max is not None and float(acc.price_per_night) <= intent.price_max:
        reasons.append(MatchReason(
            "price_match",
            f"ราคาเริ่มต้น {int(float(acc.price_per_night)):,} บาท อยู่ในงบประมาณ {int(intent.price_max):,} บาท",
        ))
        matched.append("price")

    # --- guest count (already SQL-filtered when set — always true) --------
    if intent.guest_count:
        best_room = max((rt.max_occupancy or 0 for rt in acc.room_types), default=0)
        if best_room >= intent.guest_count:
            reasons.append(MatchReason("guest_count_match", f"รองรับผู้เข้าพักได้ถึง {best_room} คน"))
            matched.append("guest_count")

    # --- facilities (already SQL-filtered when set — always true) --------
    acc_amenity_codes = {a.code for a in acc.amenities}
    for code in intent.facility_codes:
        if code in acc_amenity_codes:
            label = amenity_labels.get(code, code)
            reasons.append(MatchReason("facility_match", f"มี{label}"))
            matched.append(f"facility:{code}")

    # --- view — real data check (room_types.view_type), can genuinely miss
    if intent.view:
        view_label = VIEW_LABELS.get(intent.view, intent.view)
        if any(rt.view_type == intent.view for rt in acc.room_types):
            reasons.append(MatchReason("view_match", f"มีห้องพักหรือพื้นที่ที่มองเห็น{view_label}"))
            matched.append("view")
        else:
            reasons.append(MatchReason("view_no_data", f"ยังไม่พบข้อมูลยืนยันเกี่ยวกับ{view_label}"))
            unmatched.append("view")

    # --- atmosphere — real data check (description/tags), can genuinely miss
    for code in intent.atmosphere_codes:
        label = ATMOSPHERE_LABELS.get(code)
        if not label:
            continue
        if crud.atmosphere_match(acc, code):
            reasons.append(MatchReason("atmosphere_match", f"บรรยากาศ{label}ตามที่ค้นหา"))
            matched.append(f"atmosphere:{code}")
        else:
            reasons.append(MatchReason("atmosphere_no_data", f"ยังไม่พบข้อมูลยืนยันเกี่ยวกับบรรยากาศ{label}"))
            unmatched.append(f"atmosphere:{code}")

    # --- special conditions ---------------------------------------------
    if intent.smoking is False and acc.smoking_allowed is False:
        reasons.append(MatchReason("special_condition_match", "เป็นที่พักปลอดบุหรี่"))
        matched.append("smoking")
    if intent.extra_bed and any(rt.extra_bed_available for rt in acc.room_types):
        reasons.append(MatchReason("special_condition_match", "มีเตียงเสริมให้บริการ"))
        matched.append("extra_bed")

    reasons.sort(key=lambda r: PRIORITY.get(r.type, 9))

    match_level = None
    if matched or unmatched:
        match_level = "ตรงบางส่วน" if unmatched else "ตรงกับความต้องการมาก"

    return ReasonSet(
        reasons=reasons, matched_pois=matched_pois,
        matched_criteria=matched, unmatched_criteria=unmatched, match_level=match_level,
    )
