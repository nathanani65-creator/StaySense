"""
Seeds the `accommodations` table with the same deterministic mock data used
by the Vue frontend's src/data/mockHotels.js (same district counts, same
name-generation logic, same seeded RNG) so the API returns results that
line up with what the frontend previously showed as static mock data.

Run after schema.sql and schema_addendum.sql have been applied:
    python seed_accommodations.py
"""
from app.database import SessionLocal
from app import models

DISTRICT_INFO = {
    "เมืองพิษณุโลก": {"count": 18, "tags": ["ริมน้ำ", "แม่น้ำน่าน", "ในเมือง", "วัดใหญ่", "สะดวกเดินทาง"]},
    "พรหมพิราม": {"count": 5, "tags": ["ชนบท", "เงียบสงบ", "วิถีชุมชน"]},
    "ชาติตระการ": {"count": 4, "tags": ["ภูเขา", "ธรรมชาติ", "อากาศเย็น", "ป่าเขา"]},
    "บางกระทุ่ม": {"count": 4, "tags": ["สวนผลไม้", "ชนบท", "เงียบสงบ"]},
    "วังทอง": {"count": 4, "tags": ["ภูเขา", "น้ำตก", "วิวเขา", "ธรรมชาติ"]},
    "นครไทย": {"count": 4, "tags": ["วิวเขา", "อากาศเย็น", "ธรรมชาติ", "ภูเขา"]},
    "วัดโบสถ์": {"count": 3, "tags": ["น้ำตก", "ธรรมชาติ", "เงียบสงบ"]},
    "บางระกำ": {"count": 3, "tags": ["ทุ่งนา", "ธรรมชาติ", "ดูนก", "ชนบท"]},
    "เนินมะปราง": {"count": 3, "tags": ["ภูเขาหินปูน", "ถ้ำ", "วิวธรรมชาติ", "เงียบสงบ"]},
}

NAME_PREFIX = ["เดอะ ริเวอร์", "บ้านสวนน่าน", "แสงจันทร์", "ดาวเรือง", "ปาริชาติ", "เสน่ห์นคร", "อารยา",
               "กรีนวิว", "หลับดี", "นาคราช", "สายลม", "วิมานทอง", "ไอยรา", "ภูพิงค์", "จันทร์เจ้า",
               "อัมพวัน", "ร่มไม้", "สุขใจ", "วารีวิว", "ต้นตาล"]
NAME_SUFFIX = ["โฮเทล", "แกรนด์ โฮเทล", "บูทีค โฮเทล", "อินน์", "การ์เดน โฮเทล", "เพลส", "รีสิเดนซ์", "สวีท"]
AMENITY_CODES = ["wifi", "parking", "breakfast", "pool", "family", "pet"]

# picsum seeds for the extra gallery photos, appended after the cover so every
# mock accommodation has a 5-photo gallery (exercises the gallery + lightbox)
GALLERY_SUFFIXES = ["room", "bath", "view", "lobby"]


def make_images(base_seed: int):
    urls = [f"https://picsum.photos/seed/staysense{base_seed}/960/720"]
    urls += [f"https://picsum.photos/seed/staysense{base_seed}-{s}/960/720" for s in GALLERY_SUFFIXES]
    return [
        models.AccommodationImage(image_url=u, is_cover=(i == 0), sort_order=i)
        for i, u in enumerate(urls)
    ]


def make_rng(seed: int):
    """Same linear-congruential generator as the JS makeRng(), so results
    are bit-for-bit reproducible between frontend mock and this seed data."""
    state = seed % 2147483647
    if state <= 0:
        state += 2147483646

    def rng():
        nonlocal state
        state = (state * 16807) % 2147483647
        return (state - 1) / 2147483646

    return rng


_ROOM_AMEN_BASE = ["aircon", "wifi", "tv", "water_heater", "private_bath"]


def _enrich_room(rt: dict, rng, *, extras=(), view="none", kids=True, smoke=False, pets=False):
    """Fill the schema_addendum_7 fields + a small gallery on one room dict."""
    amen = list(_ROOM_AMEN_BASE) + list(extras)
    rt.setdefault("view_type", view)
    rt.setdefault("children_allowed", kids)
    rt.setdefault("smoking_allowed", smoke)
    rt.setdefault("pets_allowed", pets)
    rt["room_amenities_json"] = amen
    if rt.get("extra_bed_available"):
        rt.setdefault("extra_bed_max", 1 + int(rng() * 2))
    base = 900 + abs(hash(rt["name"])) % 400
    rt["_images"] = [
        f"https://picsum.photos/seed/rt{base}-{s}/900/640"
        for s in ("room", "bath", "view", "detail")
    ]
    return rt


def build_room_type(kw: dict) -> "models.RoomType":
    """Turn a make_room_types() dict (with a private `_images` list) into a
    RoomType ORM object plus its RoomTypeImage rows."""
    kw = dict(kw)
    urls = kw.pop("_images", [])
    rt = models.RoomType(**kw)
    rt.images = [models.RoomTypeImage(image_url=u, sort_order=i) for i, u in enumerate(urls)]
    return rt


def make_room_types(type_code: str, base_price: float, rng):
    """Deterministic room-type set per accommodation category, so the detail
    page's 'ประเภทห้องพัก' section has something realistic to show for the
    mock data. Real data comes from import_accommodations.py instead.

    Returns a list of models.RoomType kwargs. Each carries a private `_images`
    list (picsum URLs) that the caller pops into RoomTypeImage rows."""
    p = lambda mult: round(base_price * mult / 10) * 10

    if type_code in ("homestay", "resort"):
        rooms = [
            dict(name="บ้านพักเดี่ยว 1 ห้องนอน", price_per_night=p(1.0),
                 max_occupancy=2, standard_occupancy=2, bed_type="เตียงคู่ 1 เตียง",
                 room_size_sqm=28, breakfast_included=True,
                 extra_bed_available=True, extra_bed_price=p(0.12),
                 bedrooms=1, bathrooms=1, units_available=2 + int(rng() * 3),
                 description="บ้านหลังเดี่ยวแยกหลัง เหมาะกับคู่รักหรือครอบครัวเล็ก", sort_order=0),
            dict(name="บ้านพักครอบครัว 2 ห้องนอน", price_per_night=p(1.7),
                 max_occupancy=6, standard_occupancy=4, bed_type="เตียงคู่ 1 + เตียงเดี่ยว 2",
                 room_size_sqm=48, breakfast_included=True,
                 extra_bed_available=True, extra_bed_price=p(0.12),
                 bedrooms=2, bathrooms=2, units_available=1 + int(rng() * 3),
                 description="บ้านทั้งหลังมีครัวและระเบียงส่วนตัว พักได้ทั้งครอบครัว", sort_order=1),
        ]
        return [_enrich_room(r, rng, extras=("fridge", "desk", "balcony", "non_smoking"),
                             view="garden", pets=True) for r in rooms]

    # hotel (และประเภทอื่น ๆ ที่ไม่ระบุ) — คิดเป็น "ห้อง"
    rooms = [
        dict(name="ห้อง Standard (พัก 2 คน)", price_per_night=p(1.0),
             max_occupancy=2, standard_occupancy=2, bed_type="เตียงเดี่ยว 2 เตียง",
             room_size_sqm=24, breakfast_included=False,
             extra_bed_available=False, units_available=6 + int(rng() * 10),
             description="ห้องมาตรฐาน ขนาดกำลังดี เหมาะกับคู่รักหรือเดินทางคนเดียว", sort_order=0),
        dict(name="ห้อง Deluxe (พัก 2 คน เสริมเตียงได้)", price_per_night=p(1.35),
             max_occupancy=3, standard_occupancy=2, bed_type="เตียงคิงไซซ์ 1 เตียง",
             room_size_sqm=32, breakfast_included=True,
             extra_bed_available=True, extra_bed_price=p(0.15),
             units_available=4 + int(rng() * 6),
             description="ห้องกว้างขึ้น พร้อมอาหารเช้า เสริมเตียงได้ 1 เตียง", sort_order=1),
        dict(name="ห้อง Family (พัก 4 คน)", price_per_night=p(1.9),
             max_occupancy=4, standard_occupancy=4, bed_type="เตียงคู่ 2 เตียง",
             room_size_sqm=42, breakfast_included=True,
             extra_bed_available=True, extra_bed_price=p(0.15),
             units_available=2 + int(rng() * 4),
             description="ห้องครอบครัวขนาดใหญ่ 2 เตียงคู่ พร้อมอาหารเช้าสำหรับ 4 ท่าน", sort_order=2),
    ]
    views = ["city", "garden", "pool"]
    return [
        _enrich_room(r, rng, extras=("fridge", "desk") + (("balcony",) if i else ()) + ("non_smoking",),
                     view=views[i % len(views)])
        for i, r in enumerate(rooms)
    ]


PRICE_CONDITIONS = [
    "ราคานี้สำหรับวันธรรมดา วันหยุดนักขัตฤกษ์และเทศกาลบวกเพิ่ม 300–500 บาท/คืน",
    "เข้าพักเกินจำนวนคนมาตรฐาน คิดค่าบริการเพิ่มท่านละ 250 บาท/คืน (รวมอาหารเช้า)",
    "พักตั้งแต่ 3 คืนขึ้นไป รับส่วนลด 10% ติดต่อที่พักโดยตรง",
    "ช่วงไฮซีซั่น (พ.ย.–ก.พ.) ราคาปรับขึ้นตามประกาศของที่พัก",
]


def make_details(district, price, rng):
    """Deterministic contact info, coordinates, deposit + price conditions for
    the mock data, so the detail page's contact / pricing / map sections have
    something to show. Real data comes from import_accommodations.py."""
    lat = lng = maps_url = None
    if district.center_lat is not None and district.center_lng is not None:
        lat = round(float(district.center_lat) + (rng() - 0.5) * 0.06, 6)
        lng = round(float(district.center_lng) + (rng() - 0.5) * 0.06, 6)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"

    handle = f"{int(rng() * 9000 + 1000)}"
    is_mobile = rng() > 0.5
    phone = (
        f"08{int(rng() * 9)}-{int(rng() * 900 + 100)}-{int(rng() * 9000 + 1000)}"
        if is_mobile
        else f"055-{int(rng() * 900 + 100)}-{int(rng() * 900 + 100)}"
    )

    deposit_required = rng() > 0.45
    by_percent = deposit_required and rng() > 0.5
    advance_required = rng() > 0.6
    return dict(
        latitude=lat,
        longitude=lng,
        google_maps_url=maps_url,
        phone=phone,
        contact_line=f"@stay{handle}",
        contact_facebook=f"https://facebook.com/staysense.{handle}" if rng() > 0.35 else None,
        contact_instagram=f"@staysense_{handle}" if rng() > 0.55 else None,
        website_url=f"https://staysense-{handle}.example.com" if rng() > 0.7 else None,
        deposit_required=deposit_required,
        deposit_note="โอนมัดจำเพื่อยืนยันการจอง คืนเต็มจำนวนเมื่อเช็คเอาต์" if deposit_required else None,
        deposit_amount=None if (by_percent or not deposit_required) else round(price / 2 / 10) * 10,
        deposit_percent=30 if by_percent else None,
        advance_booking_required=advance_required,
        advance_booking_days=int(rng() * 5 + 2) if advance_required else None,
        price_conditions=PRICE_CONDITIONS[int(rng() * len(PRICE_CONDITIONS))],
    )


def backfill_room_types(db):
    """For dev DBs seeded before room types existed: add a room-type set to
    any accommodation that currently has none. Idempotent."""
    accs = (
        db.query(models.Accommodation)
        .outerjoin(models.RoomType)
        .filter(models.RoomType.id.is_(None))
        .all()
    )
    if not accs:
        return
    for acc in accs:
        rt_rng = make_rng(5000 + acc.id)
        for kw in make_room_types(acc.type.code, float(acc.price_per_night), rt_rng):
            rt = build_room_type(kw)
            rt.accommodation_id = acc.id
            db.add(rt)
    db.commit()
    print(f"Backfilled room types for {len(accs)} existing accommodations.")


def backfill_images(db):
    """Add gallery photos to mock accommodations that only have the single
    cover image (seeded before galleries existed). Idempotent."""
    accs = db.query(models.Accommodation).all()
    touched = 0
    for acc in accs:
        if len(acc.images) > 1:
            continue
        base_seed = 200 + acc.id * 7
        for i, s in enumerate(GALLERY_SUFFIXES, start=1):
            db.add(models.AccommodationImage(
                accommodation_id=acc.id,
                image_url=f"https://picsum.photos/seed/staysense{base_seed}-{s}/960/720",
                is_cover=False,
                sort_order=i,
            ))
        touched += 1
    if touched:
        db.commit()
        print(f"Backfilled gallery photos for {touched} existing accommodations.")


_ROOM_DETAIL_COLS = (
    "view_type", "room_amenities_json", "extra_bed_max",
    "children_allowed", "smoking_allowed", "pets_allowed",
)


def backfill_room_type_details(db):
    """For dev DBs whose room_types predate schema_addendum_7: fill the new
    columns (view / in-room amenities / rules) and add per-room photos.
    Idempotent — skips a room that already has a view_type set."""
    accs = db.query(models.Accommodation).all()
    touched = 0
    for acc in accs:
        rts = sorted(acc.room_types, key=lambda r: r.sort_order)
        if not rts or all(r.view_type for r in rts):
            continue
        rt_rng = make_rng(5000 + acc.id)
        generated = make_room_types(acc.type.code, float(acc.price_per_night), rt_rng)
        for existing, gen in zip(rts, generated):
            for col in _ROOM_DETAIL_COLS:
                if col in gen:
                    setattr(existing, col, gen[col])
            if not existing.images:
                existing.images = [
                    models.RoomTypeImage(image_url=u, sort_order=i)
                    for i, u in enumerate(gen.get("_images", []))
                ]
            touched += 1
    if touched:
        db.commit()
        print(f"Backfilled details/photos for {touched} existing room types.")


def backfill_details(db):
    """For dev DBs seeded before contact / coordinates / pricing-condition
    fields existed: fill them for any accommodation still missing coordinates.
    Idempotent (skips rows that already have a latitude)."""
    accs = (
        db.query(models.Accommodation)
        .filter(models.Accommodation.latitude.is_(None))
        .all()
    )
    if not accs:
        return
    for acc in accs:
        det_rng = make_rng(6000 + acc.id)
        for field, value in make_details(acc.district, float(acc.price_per_night), det_rng).items():
            setattr(acc, field, value)
    db.commit()
    print(f"Backfilled contact / location / pricing details for {len(accs)} existing accommodations.")


def run():
    db = SessionLocal()
    try:
        type_obj = db.query(models.AccommodationType).filter_by(code="hotel").first()
        if not type_obj:
            raise RuntimeError("accommodation_types has no 'hotel' row — run schema.sql first")

        amenity_by_code = {a.code: a for a in db.query(models.Amenity).all()}

        existing = db.query(models.Accommodation).count()
        if existing:
            print(f"accommodations already has {existing} rows — skipping accommodation seed (delete rows first to reseed)")
            backfill_room_types(db)
            backfill_room_type_details(db)
            backfill_details(db)
            backfill_images(db)
            return

        id_counter = 1
        created = 0
        for di, (district_name, info) in enumerate(DISTRICT_INFO.items()):
            district = db.query(models.District).filter_by(name=district_name).first()
            if not district:
                print(f"WARNING: district '{district_name}' not found, skipping")
                continue

            rng = make_rng(1000 + di * 77)
            for _ in range(info["count"]):
                prefix = NAME_PREFIX[int(rng() * len(NAME_PREFIX))]
                suffix = NAME_SUFFIX[int(rng() * len(NAME_SUFFIX))]
                name = f"{prefix} {suffix}"
                price = round((400 + rng() * 2900) / 10) * 10
                rating = round((3.5 + rng() * 1.4), 1)
                reviews = round(30 + rng() * 300)
                distance_km = round((0.3 + rng() * 9.5), 1)

                shuffled = sorted(AMENITY_CODES, key=lambda _: rng())
                amen_count = 3 + int(rng() * 3)
                amenity_codes = shuffled[:amen_count]
                if "wifi" not in amenity_codes and rng() > 0.15:
                    amenity_codes.insert(0, "wifi")

                tag_pool = info["tags"]
                tags = sorted(tag_pool, key=lambda _: rng())[: 2 + int(rng() * 2)]

                reasons = [
                    f"ใกล้{district.landmark_name} เดินทางสะดวก บรรยากาศดี เหมาะกับการพักผ่อน",
                    "ห้องพักสะอาด กว้างขวาง วิวสวย เหมาะกับครอบครัวและคู่รัก",
                    "บรรยากาศเงียบสงบ ใกล้ธรรมชาติ ราคาคุ้มค่า พนักงานบริการดี",
                    f"ทำเลดี ใกล้แหล่งท่องเที่ยวสำคัญของอำเภอ{district_name} รีวิวดีต่อเนื่อง",
                ]
                reason = reasons[int(rng() * len(reasons))]

                seed_img = 200 + id_counter * 7
                # separate RNG streams so this extra generation doesn't shift the
                # main `rng` sequence and break parity with the JS mock data
                rt_rng = make_rng(5000 + id_counter)
                det_rng = make_rng(6000 + id_counter)
                acc = models.Accommodation(
                    name=name,
                    type_id=type_obj.id,
                    district_id=district.id,
                    description=f"{name} ตั้งอยู่ในอำเภอ{district_name} {reason} มีสิ่งอำนวยความสะดวก "
                                 f"{', '.join(tags)}",
                    price_per_night=price,
                    landmark_distance_km=distance_km,
                    rating_avg=rating,
                    review_count=reviews,
                    recommended_reason=reason,
                    tags_json=tags,
                    amenities=[amenity_by_code[c] for c in amenity_codes if c in amenity_by_code],
                    images=make_images(seed_img),
                    room_types=[
                        build_room_type(kw)
                        for kw in make_room_types(type_obj.code, price, rt_rng)
                    ],
                    **make_details(district, price, det_rng),
                )
                db.add(acc)
                id_counter += 1
                created += 1

        db.commit()
        print(f"Seeded {created} accommodations.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
