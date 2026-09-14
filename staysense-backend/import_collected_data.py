"""Import real, human-collected data from staysense_data_collection.xlsx into
the database.

Usage:
    python import_collected_data.py [path/to/staysense_data_collection.xlsx]

Safe to re-run: every row in the spreadsheet carries its own stable code
(HT001, UNIT001, POI001, IMG001, NEAR001, REV001) which is stored as
`external_code` on the matching DB row, so re-running the script upserts
existing rows instead of duplicating them.

Sheet -> table mapping:
    ที่พัก                      -> accommodations (+ accommodation_amenities)
    ประเภทห้อง                  -> room_types (+ room_type_images)
    สถานที่สำคัญ (POI)          -> places
    ที่พักใกล้สถานที่สำคัญ      -> accommodation_places (curated distances)
    รูปภาพที่พัก                -> accommodation_images
    รีวิว                       -> reviews (guest reviews, no user_id)
"""
import re
import sys
from datetime import date, datetime

import openpyxl

sys.path.insert(0, ".")
from app.database import SessionLocal
from app import models
from app.semantic import index as search_index

DEFAULT_PATH = r"C:\Users\USER\Downloads\staysense_data_collection.xlsx"

AMENITY_COLUMNS = [
    (12, "aircon"), (13, "tv"), (14, "fridge"), (15, "water_heater"),
    (16, "wifi"), (17, "pool"), (18, "restaurant"), (19, "gym"),
    (20, "elevator"), (21, "breakfast"), (22, "laundry"), (23, "reception24"),
    (24, "parking"), (25, "family"), (26, "elderly"), (27, "wheelchair"),
    (28, "pet"),
]

ROOM_AMENITY_KEYWORDS = {
    "แอร์": "aircon", "ทีวี": "tv", "ตู้เย็น": "fridge",
    "เครื่องทำน้ำอุ่น": "water_heater", "wi-fi": "wifi", "wifi": "wifi",
}

POI_CATEGORY_MAP = {
    "วัด": "temple", "แหล่งท่องเที่ยว": "attraction", "สถานีรถไฟ": "station",
    "สถานีขนส่ง": "station", "ห้างสรรพสินค้า": "mall",
    "ห้างค้าปลีก-ค้าส่งขนาดใหญ่": "mall", "โรงพยาบาล": "hospital",
    "ตลาด": "market", "ร้านสะดวกซื้อ": "convenience", "ร้านอาหาร": "restaurant",
    "พิพิธภัณฑ์": "museum", "สนามบิน": "airport",
}

VIEW_KEYWORDS = [
    ("ภูเขา", "mountain"), ("แม่น้ำ", "river"), ("ทะเลสาบ", "river"),
    ("อ่างเก็บน้ำ", "river"), ("สระ", "pool"), ("เมือง", "city"),
    ("สวน", "garden"),
]


def yn(value) -> bool | None:
    if value is None:
        return None
    s = str(value).strip().upper()
    if s == "Y":
        return True
    if s == "N":
        return False
    return None


def clean_str(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def parse_price(value) -> float | None:
    """'1,100 ' -> 1100.0 ; '1,400 - 1,600' -> 1400.0 (starting price)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace(",", "").strip()
    if not s:
        return None
    first = re.split(r"[-–]", s)[0].strip()
    try:
        return float(first)
    except ValueError:
        return None


def parse_distance_km(value) -> float | None:
    """7.9 -> 7.9 ; '450 เมตร' -> 0.45 ; '750 ม.' -> 0.75."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    s = str(value).strip()
    m = re.match(r"([\d.]+)\s*(เมตร|ม\.)", s)
    if m:
        return round(float(m.group(1)) / 1000, 2)
    m = re.match(r"([\d.]+)", s)
    return round(float(m.group(1)), 2) if m else None


def parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value) -> datetime | None:
    d = parse_date(value)
    return datetime.combine(d, datetime.min.time()) if d else None


def detect_type_code(text: str) -> str:
    if "โฮมสเตย์" in text:
        return "homestay"
    if "รีสอร์" in text:
        return "resort"
    return "hotel"


def detect_place_category(text: str) -> str:
    return POI_CATEGORY_MAP.get((text or "").strip(), "attraction")


def detect_view_type(text: str | None) -> str | None:
    if not text:
        return None
    for kw, code in VIEW_KEYWORDS:
        if kw in text:
            return code
    return None


def split_urls(value) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[\n,]+", str(value))
    return [p.strip() for p in parts if p.strip()]


def rows_of(ws):
    return [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]


def import_accommodations(db, ws) -> dict[str, int]:
    code_to_id = {}
    types = {t.code: t.id for t in db.query(models.AccommodationType).all()}
    districts = {d.name.strip(): d.id for d in db.query(models.District).all()}
    amenities = {a.code: a for a in db.query(models.Amenity).all()}

    for r in rows_of(ws):
        ext = clean_str(r[0])
        if not clean_str(r[1]):
            print(f"  !! skip {ext}: no name")
            continue

        acc = db.query(models.Accommodation).filter_by(external_code=ext).first()
        if not acc:
            acc = models.Accommodation(external_code=ext)
            db.add(acc)

        type_code = detect_type_code(clean_str(r[2]) or "")
        district_name = (clean_str(r[3]) or "").strip()
        if district_name not in districts:
            print(f"  !! skip {ext}: unknown district '{district_name}'")
            continue
        price = parse_price(r[7])
        if price is None:
            print(f"  !! skip {ext}: no starting price")
            continue

        reasons = [clean_str(r[i]) for i in (46, 47, 48)]
        reasons = [x for x in reasons if x]
        recommended_reason = " • ".join(reasons) if reasons else clean_str(r[49])

        pet_note = clean_str(r[29])
        price_conditions = f"เงื่อนไขสัตว์เลี้ยง: {pet_note}" if pet_note else None

        payment_methods = [p.strip() for p in (clean_str(r[37]) or "").split(",") if p.strip()]
        tags = [t.strip() for t in (clean_str(r[44]) or "").split(",") if t.strip()]

        acc.name = clean_str(r[1])
        acc.type_id = types[type_code]
        acc.district_id = districts[district_name]
        acc.address = clean_str(r[4])
        acc.latitude = r[5]
        acc.longitude = r[6]
        acc.price_per_night = price
        acc.description = clean_str(r[8])
        acc.google_maps_url = clean_str(r[9])
        acc.landmark_distance_km = r[10] if isinstance(r[10], (int, float)) else None
        acc.checkin_time = clean_str(r[30])
        acc.checkout_time = clean_str(r[31])
        acc.cancellation_policy = clean_str(r[32])
        acc.min_age = int(r[33]) if isinstance(r[33], (int, float)) else None
        acc.smoking_allowed = yn(r[34])
        acc.deposit_required = bool(yn(r[35]))
        acc.deposit_note = clean_str(r[36])
        acc.payment_methods_json = payment_methods or None
        acc.price_conditions = price_conditions
        acc.phone = clean_str(r[38])
        acc.contact_line = clean_str(r[39])
        acc.contact_facebook = clean_str(r[40])
        acc.website_url = clean_str(r[41])
        acc.tags_json = tags or None
        acc.recommended_reason = recommended_reason
        acc.source_note = clean_str(r[51])
        acc.last_verified_at = parse_date(r[52])
        acc.status = "published"

        acc.amenities = [amenities[code] for col, code in AMENITY_COLUMNS if yn(r[col]) and code in amenities]

        db.flush()
        code_to_id[ext] = acc.id
        print(f"  ok {ext}: {acc.name} (id={acc.id})")

    db.commit()
    return code_to_id


def import_room_types(db, ws, acc_ids: dict[str, int]):
    for r in rows_of(ws):
        ext = clean_str(r[0])
        acc_code = clean_str(r[1])
        acc_id = acc_ids.get(acc_code)
        if not acc_id:
            print(f"  !! skip {ext}: unknown accommodation code '{acc_code}'")
            continue
        if not clean_str(r[4]):
            print(f"  !! skip {ext}: no room name")
            continue
        rt_price = parse_price(r[6])
        if rt_price is None:
            print(f"  !! skip {ext}: no starting price")
            continue

        rt = db.query(models.RoomType).filter_by(external_code=ext).first()
        if not rt:
            rt = models.RoomType(external_code=ext, accommodation_id=acc_id)
            db.add(rt)

        desc = clean_str(r[5])
        extra_note = clean_str(r[30])
        if extra_note:
            desc = f"{desc} — {extra_note}" if desc else extra_note

        room_amenities = []
        for part in (clean_str(r[27]) or "").split(","):
            part = part.strip()
            code = ROOM_AMENITY_KEYWORDS.get(part) or ROOM_AMENITY_KEYWORDS.get(part.lower())
            if code and code not in room_amenities:
                room_amenities.append(code)

        rt.accommodation_id = acc_id
        rt.name = clean_str(r[4])
        rt.price_per_night = rt_price
        rt.standard_occupancy = int(r[9]) if isinstance(r[9], (int, float)) else None
        rt.max_occupancy = int(r[10]) if isinstance(r[10], (int, float)) else None
        rt.bedrooms = int(r[13]) if isinstance(r[13], (int, float)) else None
        rt.bathrooms = int(r[14]) if isinstance(r[14], (int, float)) else None
        rt.bed_type = clean_str(r[15])
        rt.room_size_sqm = r[16] if isinstance(r[16], (int, float)) else None
        rt.extra_bed_available = bool(yn(r[17]))
        rt.extra_bed_price = r[19] if isinstance(r[19], (int, float)) else None
        rt.extra_bed_max = int(r[20]) if isinstance(r[20], (int, float)) else None
        rt.breakfast_included = bool(yn(r[23]))
        rt.units_available = int(r[24]) if isinstance(r[24], (int, float)) else None
        rt.view_type = detect_view_type(clean_str(r[26]))
        rt.room_amenities_json = room_amenities or None
        rt.smoking_allowed = yn(r[28])
        rt.pets_allowed = yn(r[29])
        rt.description = desc

        image_urls = split_urls(r[31])
        rt.images = [
            models.RoomTypeImage(image_url=url, sort_order=i) for i, url in enumerate(image_urls)
        ]

        db.flush()
        print(f"  ok {ext}: {rt.name} (accommodation {acc_code})")

    db.commit()


def import_places(db, ws) -> dict[str, int]:
    code_to_id = {}
    districts = {d.name.strip(): d.id for d in db.query(models.District).all()}

    for r in rows_of(ws):
        ext = clean_str(r[0])
        if not clean_str(r[1]) or not isinstance(r[5], (int, float)) or not isinstance(r[6], (int, float)):
            print(f"  !! skip {ext}: missing name or coordinates")
            continue

        place = db.query(models.Place).filter_by(external_code=ext).first()
        if not place:
            place = models.Place(external_code=ext)
            db.add(place)

        district_name = (clean_str(r[3]) or "").strip()

        place.name = clean_str(r[1])
        place.category = detect_place_category(clean_str(r[2]))
        place.district_id = districts.get(district_name)
        place.address = clean_str(r[4])
        place.latitude = r[5]
        place.longitude = r[6]
        place.source_note = clean_str(r[8])

        db.flush()
        code_to_id[ext] = place.id
        print(f"  ok {ext}: {place.name} ({place.category})")

    db.commit()
    return code_to_id


def import_accommodation_places(db, ws, acc_ids: dict[str, int], place_ids: dict[str, int]):
    for r in rows_of(ws):
        ext = clean_str(r[0])
        acc_id = acc_ids.get(clean_str(r[1]))
        place_id = place_ids.get(clean_str(r[3]))
        if not acc_id or not place_id:
            print(f"  !! skip {ext}: unresolved accommodation/place code")
            continue

        link = db.query(models.AccommodationPlace).filter_by(external_code=ext).first()
        if not link:
            link = models.AccommodationPlace(external_code=ext, accommodation_id=acc_id, place_id=place_id)
            db.add(link)

        link.accommodation_id = acc_id
        link.place_id = place_id
        # column 6 (straight-line) and 7 (route) are identical throughout the
        # sheet — prefer 7 since it's the one meant to reflect real travel.
        link.distance_km = parse_distance_km(r[7]) or parse_distance_km(r[6])
        link.travel_time_minutes = int(r[8]) if isinstance(r[8], (int, float)) else None
        link.travel_method = clean_str(r[9])
        link.note = clean_str(r[10])
        link.route_url = clean_str(r[11])
        link.verified_at = parse_date(r[12])
        link.source_note = clean_str(r[13])

        db.flush()
        print(f"  ok {ext}: accommodation {r[1]} <-> place {r[3]} ({link.distance_km} km)")

    db.commit()


def import_images(db, ws, acc_ids: dict[str, int]):
    for r in rows_of(ws):
        ext = clean_str(r[0])
        acc_id = acc_ids.get(clean_str(r[1]))
        if not acc_id:
            print(f"  !! skip {ext}: unknown accommodation code '{r[1]}'")
            continue

        # a handful of rows have more than one URL jammed into the same cell
        # (newline- or comma-separated) — split into one image row each,
        # suffixing the external_code (IMG004, IMG004-2, ...) to keep it unique.
        urls = split_urls(r[4])
        if not urls:
            print(f"  !! skip {ext}: no image URL")
            continue

        category = clean_str(r[3])
        for i, image_url in enumerate(urls):
            sub_ext = ext if i == 0 else f"{ext}-{i + 1}"
            img = db.query(models.AccommodationImage).filter_by(external_code=sub_ext).first()
            if not img:
                img = models.AccommodationImage(external_code=sub_ext, accommodation_id=acc_id)
                db.add(img)

            img.accommodation_id = acc_id
            img.image_url = image_url
            img.caption = clean_str(r[5])
            img.is_cover = i == 0 and (category == "ภาพปก" or bool(yn(r[6])))
            img.sort_order = (int(r[7]) if isinstance(r[7], (int, float)) else 0) + i
            img.source_note = clean_str(r[8])

            db.flush()
            print(f"  ok {sub_ext}: accommodation {r[1]} ({'cover' if img.is_cover else category})")

    db.commit()


def to_5_scale(value) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    return max(1, min(5, round(value / 2)))


def import_reviews(db, ws, acc_ids: dict[str, int]):
    for r in rows_of(ws):
        ext = clean_str(r[0])
        if clean_str(r[14]) and clean_str(r[14]) != "ข้อมูลจริง":
            print(f"  !! skip {ext}: not marked as real data ('{r[14]}')")
            continue
        acc_id = acc_ids.get(clean_str(r[1]))
        if not acc_id:
            print(f"  !! skip {ext}: unknown accommodation code '{r[1]}'")
            continue
        rating = to_5_scale(r[3])
        if rating is None:
            print(f"  !! skip {ext}: no overall rating")
            continue

        review = db.query(models.Review).filter_by(external_code=ext).first()
        is_new = review is None
        if not review:
            review = models.Review(external_code=ext, accommodation_id=acc_id)
            db.add(review)

        review.accommodation_id = acc_id
        review.user_id = None
        review.guest_name = clean_str(r[12]) or "ผู้เข้าพัก"
        review.rating = rating
        review.cleanliness_rating = to_5_scale(r[4])
        review.location_rating = to_5_scale(r[5])
        review.service_rating = to_5_scale(r[6])
        review.value_rating = to_5_scale(r[7])
        review.comment = clean_str(r[8])
        created = parse_datetime(r[10])
        if created and is_new:
            review.created_at = created

        db.flush()
        print(f"  ok {ext}: {review.guest_name} -> accommodation {r[1]} ({review.rating}/5)")

    db.commit()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    print(f"Reading {path}")
    wb = openpyxl.load_workbook(path, data_only=True)
    db = SessionLocal()

    print("\n== ที่พัก (accommodations) ==")
    acc_ids = import_accommodations(db, wb["ที่พัก"])

    print("\n== ประเภทห้อง (room types) ==")
    import_room_types(db, wb["ประเภทห้อง"], acc_ids)

    print("\n== สถานที่สำคัญ (POI) (places) ==")
    place_ids = import_places(db, wb["สถานที่สำคัญ (POI)"])

    print("\n== ที่พักใกล้สถานที่สำคัญ (curated distances) ==")
    import_accommodation_places(db, wb["ที่พักใกล้สถานที่สำคัญ"], acc_ids, place_ids)

    print("\n== รูปภาพที่พัก (images) ==")
    import_images(db, wb["รูปภาพที่พัก"], acc_ids)

    print("\n== รีวิว (reviews) ==")
    import_reviews(db, wb["รีวิว"], acc_ids)

    print("\nRebuilding semantic search index...")
    count = search_index.build_index(db)
    print(f"Indexed {count} accommodations.")

    print("\nDone.")


if __name__ == "__main__":
    main()
