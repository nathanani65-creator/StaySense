"""The "understand the query" pipeline shared by /api/search, /api/search/nearby
and /api/search/suggestions:

  normalize_query()  -- fixes typos/abbreviations/informal terms using the
                         search_terms dictionary (+ a fuzzy-match fallback)
  parse_intent()     -- pulls structured fields (type, district, price,
                         guest count, facilities, POI, "near me", ...) out of
                         the normalized text

Supersedes the old app/nearby_intent.py — every keyword table here maps to
real data already in the database (accommodation_types.code, amenities.code,
places.category/name, districts.name); nothing invents a category or a
place that isn't already stored.
"""

import re
import threading
from dataclasses import dataclass, field

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from . import models
from .crud import ATMOSPHERE_KEYWORDS

# ---------------------------------------------------------------- dictionary

@dataclass(frozen=True)
class _Term:
    input_term: str
    canonical_term: str
    term_type: str


_lock = threading.Lock()
_terms_cache: list[_Term] | None = None


def _load_terms(db: Session) -> list[_Term]:
    # cache plain data, not ORM instances — a SearchTerm row loaded under one
    # request's session would raise DetachedInstanceError if touched again
    # after that session closes (get_db() opens/closes a fresh one per call).
    global _terms_cache
    with _lock:
        if _terms_cache is None:
            rows = db.query(models.SearchTerm).filter(models.SearchTerm.status == "active").all()
            _terms_cache = [_Term(r.input_term, r.canonical_term, r.term_type) for r in rows]
        return list(_terms_cache)


def reload_terms_cache() -> None:
    """Call after any admin edit to search_terms (no admin UI yet, but kept
    so a future one has a hook to invalidate the cache)."""
    global _terms_cache
    with _lock:
        _terms_cache = None


@dataclass
class TermCorrection:
    original: str
    canonical: str
    term_type: str


@dataclass
class NormalizeResult:
    original: str
    normalized: str
    corrections: list[TermCorrection] = field(default_factory=list)
    confidence: float = 1.0


FUZZY_MIN_LEN = 3          # don't fuzzy-match single characters / very short substrings
FUZZY_THRESHOLD = 82.0     # rapidfuzz ratio (0-100)


def normalize_query(db: Session, text: str, *, skip_correction: bool = False) -> NormalizeResult:
    text = text or ""
    if skip_correction:
        # "ใช้ข้อความเดิม" — the visitor explicitly rejected a low-confidence
        # correction, so search with exactly what they typed (spec §10).
        return NormalizeResult(original=text, normalized=text, corrections=[], confidence=1.0)
    terms = sorted(_load_terms(db), key=lambda t: len(t.input_term), reverse=True)

    normalized = text
    corrections: list[TermCorrection] = []

    # pass 1: exact dictionary substrings, longest input_term first so e.g.
    # "โฮมสเตย" (7 chars) is tried before any shorter accidental overlap.
    matched_spans: list[tuple[int, int]] = []
    for term in terms:
        idx = normalized.find(term.input_term)
        if idx == -1:
            continue
        normalized = normalized.replace(term.input_term, term.canonical_term)
        corrections.append(TermCorrection(term.input_term, term.canonical_term, term.term_type))
        matched_spans.append((idx, idx + len(term.input_term)))

    fuzzy_used = False
    if not corrections:
        # pass 2: best-effort fuzzy fallback for typos not in the dictionary.
        # Thai has no whitespace between words in general, so there's no safe
        # way to slice arbitrary substrings out of the query and fuzzy-match
        # them — a same-length window sliced across a correct word can itself
        # look like a typo (e.g. slicing "สระว่ายน้ำ" into a 9-char window
        # drops a character and now resembles the *typo* "สะว่ายน้ำ"),
        # corrupting already-correct text. To stay safe without a proper Thai
        # tokenizer, this pass only ever compares/replaces whole
        # whitespace-delimited tokens — never a mid-word slice — and skips
        # any token that's already a recognized correct word.
        known_correct = {t.canonical_term for t in terms}
        tokens = re.split(r"(\s+)", text)
        for i, tok in enumerate(tokens):
            if not tok.strip() or tok in known_correct:
                continue
            best_term, best_ratio = None, 0.0
            for term in terms:
                if len(term.input_term) < FUZZY_MIN_LEN or abs(len(tok) - len(term.input_term)) > 1:
                    continue
                if tok == term.input_term:
                    continue  # pass 1 already handles exact matches
                ratio = fuzz.ratio(tok, term.input_term)
                if ratio >= FUZZY_THRESHOLD and ratio > best_ratio:
                    best_term, best_ratio = term, ratio
            if best_term:
                tokens[i] = best_term.canonical_term
                corrections.append(TermCorrection(tok, best_term.canonical_term, best_term.term_type))
                fuzzy_used = True
        if fuzzy_used:
            normalized = "".join(tokens)

    confidence = 0.6 if fuzzy_used else 1.0
    return NormalizeResult(original=text, normalized=normalized, corrections=corrections, confidence=confidence)


# ------------------------------------------------------------------ parsing

TYPE_KEYWORDS = {
    "โรงแรม": "hotel",
    "รีสอร์ต": "resort",
    "โฮมสเตย์": "homestay",
}

NEAR_ME_KEYWORDS = [
    "ใกล้ฉัน", "แถวนี้", "ใกล้ตัว", "ใกล้ตำแหน่งปัจจุบัน", "บริเวณนี้",
    "ใกล้ๆ", "ใกล้ ๆ", "near me",
]

POI_CATEGORY_KEYWORDS = {
    "วัด": "temple", "ศาสนสถาน": "temple",
    "ห้างสรรพสินค้า": "mall", "ห้าง": "mall", "ศูนย์การค้า": "mall",
    "โรงพยาบาล": "hospital",
    "สถานีขนส่ง": "station", "สถานีรถไฟ": "station", "ท่ารถ": "station",
    "ร้านอาหาร": "restaurant",
    "ร้านสะดวกซื้อ": "convenience",
    "ตลาด": "market",
    "มหาวิทยาลัย": "university",
    "สถานบันเทิง": "nightlife",
    "แหล่งท่องเที่ยว": "attraction", "สถานที่ท่องเที่ยว": "attraction",
    "พิพิธภัณฑ์": "museum",
    "สนามบิน": "airport",
}

PRICE_TRIGGER_WORDS = ["บาท", "ราคา", "งบ", "ไม่เกิน", "ต่ำกว่า", "ประมาณ"]
PRICE_PATTERN = re.compile(r"\d{3,6}")
GUEST_COUNT_PATTERN = re.compile(r"(?:สำหรับ|พัก)?\s*(\d{1,2})\s*คน")

# room_types.view_type ENUM values (garden|river|city|mountain|pool|none) —
# spec §7/§9: "วิวภูเขา" is a distinct, verifiable criterion (checked against
# real room_types rows), separate from the "atmosphere" tag match.
VIEW_KEYWORDS = {
    "วิวภูเขา": "mountain", "ภูเขา": "mountain",
    "วิวแม่น้ำ": "river", "แม่น้ำ": "river",
    "วิวเมือง": "city",
    "วิวสวน": "garden",
    "วิวสระว่ายน้ำ": "pool",
}
VIEW_LABELS = {"mountain": "วิวภูเขา", "river": "วิวแม่น้ำ", "city": "วิวเมือง", "garden": "วิวสวน", "pool": "วิวสระว่ายน้ำ"}


@dataclass
class ParsedIntent:
    accommodation_type_code: str | None = None
    district_name: str | None = None
    price_max: float | None = None
    guest_count: int | None = None
    facility_codes: list[str] = field(default_factory=list)
    atmosphere_codes: list[str] = field(default_factory=list)
    view: str | None = None                # room_types.view_type match — garden|river|city|mountain|pool
    smoking: bool | None = None            # True = must allow smoking, False = must be smoke-free
    extra_bed: bool | None = None
    poi_category: str | None = None
    poi_id: int | None = None
    poi_name: str | None = None
    nearby_intent: bool = False
    use_current_location: bool = False

    def as_dict(self) -> dict:
        return {
            "accommodationType": self.accommodation_type_code,
            "district": self.district_name,
            "priceMax": self.price_max,
            "guestCount": self.guest_count,
            "facilities": self.facility_codes,
            "atmosphere": self.atmosphere_codes,
            "view": self.view,
            "smoking": self.smoking,
            "extraBed": self.extra_bed,
            "poiCategory": self.poi_category,
            "poiId": self.poi_id,
            "poiName": self.poi_name,
            "nearbyIntent": self.nearby_intent,
            "useCurrentLocation": self.use_current_location,
        }


def _detect_type(text: str) -> str | None:
    for kw, code in TYPE_KEYWORDS.items():
        if kw in text:
            return code
    return None


def _detect_district(text: str, districts: list["models.District"]) -> str | None:
    for d in sorted(districts, key=lambda d: len(d.name), reverse=True):
        if d.name in text:
            return d.name
    if d_muang := next((d for d in districts if d.name == "เมืองพิษณุโลก"), None):
        if "พิษณุโลก" in text:
            return d_muang.name
    return None


def _detect_price_max(text: str) -> float | None:
    if not any(w in text for w in PRICE_TRIGGER_WORDS):
        return None
    match = PRICE_PATTERN.search(text.replace(",", ""))
    return float(match.group()) if match else None


def _detect_guest_count(text: str) -> int | None:
    match = GUEST_COUNT_PATTERN.search(text)
    return int(match.group(1)) if match else None


def _detect_facilities(text: str, amenities: list["models.Amenity"]) -> list[str]:
    found = []
    for a in amenities:
        if a.label_th and a.label_th in text and a.code not in found:
            found.append(a.code)
    # a few short keywords that don't literally appear in label_th
    aliases = {"ครอบครัว": "family", "รถเข็น": "wheelchair", "สัตว์เลี้ยง": "pet"}
    for kw, code in aliases.items():
        if kw in text and code not in found and any(a.code == code for a in amenities):
            found.append(code)
    return found


def _detect_atmosphere(text: str) -> list[str]:
    found = []
    for code, keywords in ATMOSPHERE_KEYWORDS.items():
        if code == "family":
            continue  # "family" here means suitable_for, handled as a facility (amenity code 'family')
        if any(kw in text for kw in keywords):
            found.append(code)
    return found


def _detect_smoking(text: str) -> bool | None:
    if "ปลอดบุหรี่" in text:
        return False
    if "สูบบุหรี่ได้" in text:
        return True
    return None


def _detect_extra_bed(text: str) -> bool | None:
    return True if "เตียงเสริม" in text else None


def _detect_view(text: str) -> str | None:
    for kw in sorted(VIEW_KEYWORDS, key=len, reverse=True):
        if kw in text:
            return VIEW_KEYWORDS[kw]
    return None


def _detect_poi(text: str, places: list["models.Place"]) -> tuple[str | None, int | None, str | None]:
    """Specific place names win over a bare category — "วัดนางพญา" resolves
    to that exact place, not just poi_category=temple."""
    for p in sorted(places, key=lambda p: len(p.name), reverse=True):
        if p.name in text:
            return p.category, p.id, p.name
    for kw in sorted(POI_CATEGORY_KEYWORDS, key=len, reverse=True):
        if kw in text:
            return POI_CATEGORY_KEYWORDS[kw], None, None
    return None, None, None


def parse_intent(db: Session, normalized_text: str) -> ParsedIntent:
    text = normalized_text or ""
    amenities = db.query(models.Amenity).all()
    districts = db.query(models.District).all()
    places = db.query(models.Place).all()

    near_me = any(kw.lower() in text.lower() for kw in NEAR_ME_KEYWORDS)
    poi_category, poi_id, poi_name = _detect_poi(text, places)
    has_near_word = "ใกล้" in text or "แถวนี้" in text or "บริเวณนี้" in text

    return ParsedIntent(
        accommodation_type_code=_detect_type(text),
        district_name=_detect_district(text, districts),
        price_max=_detect_price_max(text),
        guest_count=_detect_guest_count(text),
        facility_codes=_detect_facilities(text, amenities),
        atmosphere_codes=_detect_atmosphere(text),
        view=_detect_view(text),
        smoking=_detect_smoking(text),
        extra_bed=_detect_extra_bed(text),
        poi_category=poi_category,
        poi_id=poi_id,
        poi_name=poi_name,
        nearby_intent=near_me or (has_near_word and bool(poi_category or poi_id)),
        use_current_location=near_me,
    )


def build_interpreted_as(intent: ParsedIntent, type_labels: dict[str, str], poi_labels: dict[str, str]) -> str:
    """Human-readable Thai recap of what was understood, e.g.
    'โรงแรมใกล้วัด มีสระว่ายน้ำ ราคาไม่เกิน 1,500 บาท' — shown to the user
    so they can sanity-check the interpretation (spec §4/§10)."""
    parts = []
    if intent.accommodation_type_code:
        parts.append(type_labels.get(intent.accommodation_type_code, ""))
    else:
        parts.append("ที่พัก")
    if intent.poi_name:
        parts.append(f"ใกล้{intent.poi_name}")
    elif intent.poi_category:
        parts.append(f"ใกล้{poi_labels.get(intent.poi_category, intent.poi_category)}")
    elif intent.use_current_location:
        parts.append("ใกล้ฉัน")
    if intent.view:
        parts.append(VIEW_LABELS.get(intent.view, intent.view))
    if intent.district_name:
        parts.append(f"ในอำเภอ{intent.district_name}")
    if intent.guest_count:
        parts.append(f"สำหรับ {intent.guest_count} คน")
    if intent.price_max is not None:
        parts.append(f"ราคาไม่เกิน {int(intent.price_max):,} บาท")
    return " ".join(parts)
