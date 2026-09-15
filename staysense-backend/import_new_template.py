"""
One-off importer for the richer staysense_data_collection template (the one
with separate ที่พัก / ประเภทห้อง / สถานที่สำคัญ (POI) / ที่พักใกล้สถานที่สำคัญ /
รูปภาพที่พัก / รีวิว sheets) — targets ONLY the accommodation codes listed in
TARGET_CODES, so re-running never touches the 12 accommodations already
curated in the database from the older template.

Usage:
    python import_new_template.py "path/to/file.xlsx" [--dry-run]
"""
import argparse
import sys

import pandas as pd

from app.database import SessionLocal
from app import models

try:
    from app.semantic import index as search_index
except Exception:
    search_index = None

TARGET_CODES = {"RS005", "RS006", "HT006", "HT007"}  # HT005 (ezzenhotel) skipped: no lat/lng/price in the sheet

AMENITY_COLUMN_MAP = {
    "แอร์ (Y/N)": "aircon",
    "ทีวี (Y/N)": "tv",
    "ตู้เย็น (Y/N)": "fridge",
    "เครื่องทำน้ำอุ่น (Y/N)": "water_heater",
    "Wi-Fi (Y/N)": "wifi",
    "สระว่ายน้ำ (Y/N)": "pool",
    "ร้านอาหาร (Y/N)": "restaurant",
    "ฟิตเนส (Y/N)": "gym",
    "ลิฟต์ (Y/N)": "elevator",
    "อาหารเช้า (Y/N)": "breakfast",
    "บริการซักรีด (Y/N)": "laundry",
    "แผนกต้อนรับ 24 ชม. (Y/N)": "reception24",
    "ที่จอดรถ (Y/N)": "parking",
    "รองรับเด็ก (Y/N)": "family",
    "รองรับผู้สูงอายุ (Y/N)": "elderly",
    "รองรับรถเข็น (Y/N)": "wheelchair",
    "สัตว์เลี้ยงเข้าพักได้ (Y/N)": "pet",
}

VIEW_KEYWORDS = [
    ("ภูเขา", "mountain"), ("แม่น้ำ", "river"), ("ทะเลสาบ", "river"),
    ("สระ", "pool"), ("สวน", "garden"), ("เมือง", "city"),
]

TYPE_ALIASES = {"รีสอร์ท": "รีสอร์ต"}  # sheet spells it with ท, our accommodation_types.name_th uses ต

CATEGORY_MAP = {
    "วัด": "temple", "ศาสนสถาน": "temple",
    "ห้างสรรพสินค้า": "mall", "ศูนย์การค้า": "mall",
    "โรงพยาบาล": "hospital",
    "สถานีรถไฟ": "station", "สถานีขนส่ง": "station",
    "ร้านอาหาร": "restaurant",
    "ร้านสะดวกซื้อ": "convenience",
    "ตลาด": "market",
    "มหาวิทยาลัย": "university",
    "สถานบันเทิง": "nightlife",
    "แหล่งท่องเที่ยว": "attraction", "สถานที่ท่องเที่ยว": "attraction",
    "พิพิธภัณฑ์": "museum",
    "สนามบิน": "airport",
}


def clean(value, default=None):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    text = str(value).strip()
    if text.lower() in ("nan", "none", ""):
        return default
    return text


def parse_yn(value):
    text = (clean(value) or "").upper()
    if text == "Y":
        return True
    if text == "N":
        return False
    return None


def parse_price(value):
    """Handles plain numbers and ranges like '350-490' / '743 – 860' by
    taking the lower bound (shown as the "starting price")."""
    text = clean(value)
    if text is None:
        return None
    text = text.replace(",", "")
    for sep in ("–", "-", "~"):
        if sep in text:
            text = text.split(sep)[0].strip()
            break
    try:
        return float(text)
    except ValueError:
        return None


def clip(value, maxlen):
    """Drop (never truncate — a cut-off URL is often invalid) a string
    that would overflow its column, rather than crash the whole row."""
    if value is None:
        return None
    return value if len(value) <= maxlen else None


def to_5_scale(value):
    """Sheet ratings are on Booking.com's 0-10 scale; reviews.rating has a
    CHECK (rating BETWEEN 1 AND 5) constraint, matching every other rating
    already in the system (rating_avg etc. are all 5-point)."""
    if value is None or pd.isna(value):
        return None
    return max(1, min(5, round(float(value) / 2)))


def detect_view(text):
    text = text or ""
    for kw, code in VIEW_KEYWORDS:
        if kw in text:
            return code
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("excel_path")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = args.excel_path
    acc_df = pd.read_excel(path, sheet_name="ที่พัก")
    room_df = pd.read_excel(path, sheet_name="ประเภทห้อง")
    poi_df = pd.read_excel(path, sheet_name="สถานที่สำคัญ (POI)")
    link_df = pd.read_excel(path, sheet_name="ที่พักใกล้สถานที่สำคัญ")
    img_df = pd.read_excel(path, sheet_name="รูปภาพที่พัก")
    review_df = pd.read_excel(path, sheet_name="รีวิว")

    acc_df = acc_df[acc_df["รหัสที่พัก"].isin(TARGET_CODES)]
    if acc_df.empty:
        print("ไม่พบแถวที่พักที่ตรงกับ TARGET_CODES — ไม่มีอะไรให้นำเข้า")
        return

    db = SessionLocal()
    type_lookup = {t.name_th: t for t in db.query(models.AccommodationType).all()}
    district_lookup = {d.name: d for d in db.query(models.District).all()}
    amenity_lookup = {a.code: a for a in db.query(models.Amenity).all()}
    place_lookup = {p.name: p for p in db.query(models.Place).all()}
    poi_by_code = {}

    code_to_acc = {}  # รหัสที่พัก -> Accommodation instance
    errors = []

    # ---- 1. accommodations -------------------------------------------------
    for _, row in acc_df.iterrows():
        code = clean(row.get("รหัสที่พัก"))
        name = clean(row.get("ชื่อที่พัก"))
        try:
            type_name = clean(row.get("ประเภทที่พัก"))
            district_name = clean(row.get("อำเภอ"))
            type_obj = type_lookup.get(type_name) or type_lookup.get(TYPE_ALIASES.get(type_name))
            district_obj = district_lookup.get(district_name)
            if not type_obj:
                raise ValueError(f"ไม่รู้จักประเภท '{type_name}'")
            if not district_obj:
                raise ValueError(f"ไม่รู้จักอำเภอ '{district_name}'")

            lat, lng = row.get("ละติจูด"), row.get("ลองจิจูด")
            price = parse_price(row.get("ราคาเริ่มต้น (บาท/คืน)"))
            if pd.isna(lat) or pd.isna(lng):
                raise ValueError("ไม่มีพิกัดละติจูด/ลองจิจูด")
            if price is None:
                raise ValueError("ไม่มีราคาต่อคืน")

            amenity_objs = []
            for col, code_name in AMENITY_COLUMN_MAP.items():
                if parse_yn(row.get(col)) is True:
                    a = amenity_lookup.get(code_name)
                    if a:
                        amenity_objs.append(a)

            existing = db.query(models.Accommodation).filter_by(name=name, district_id=district_obj.id).first()
            target = existing or models.Accommodation(name=name, district_id=district_obj.id)
            target.type_id = type_obj.id
            target.address = clip(clean(row.get("ที่อยู่เต็ม")), 255)
            target.latitude = float(lat)
            target.longitude = float(lng)
            target.price_per_night = price
            target.description = clean(row.get("คำอธิบายเกี่ยวกับที่พัก"))
            target.amenities = amenity_objs
            target.checkin_time = clean(row.get("เวลาเช็กอิน"))
            target.checkout_time = clean(row.get("เวลาเช็กเอาต์"))
            target.cancellation_policy = clean(row.get("นโยบายยกเลิก/คืนเงิน"))
            min_age = row.get("อายุขั้นต่ำผู้เช็กอิน (ปี)")
            target.min_age = int(min_age) if not pd.isna(min_age) else None
            target.smoking_allowed = parse_yn(row.get("สูบบุหรี่ได้ (Y/N)"))
            target.deposit_required = bool(parse_yn(row.get("ต้องวางมัดจำ (Y/N)")))
            target.deposit_note = clip(clean(row.get("รายละเอียดเงินมัดจำ")), 255)
            payment = clean(row.get("วิธีชำระเงิน"))
            target.payment_methods_json = [p.strip() for p in payment.split(",")] if payment else None
            target.contact_line = clip(clean(row.get("LINE")), 120)
            target.contact_facebook = clip(clean(row.get("Facebook")), 255)
            target.website_url = clip(clean(row.get("เว็บไซต์ที่พัก")), 255)
            target.google_maps_url = clip(clean(row.get("ลิงก์แผนที่")), 500)
            target.status = "published"
            target.source_note = clip(clean(row.get("แหล่งข้อมูล/ลิงก์อ้างอิง")), 500)
            target.phone = clip(clean(row.get("เบอร์โทรศัพท์")), 20)

            if not args.dry_run:
                if not existing:
                    db.add(target)
                # commit each accommodation on its own — a later row's
                # failure must never roll back an earlier row that already
                # succeeded (they'd otherwise share one open transaction)
                db.commit()
            code_to_acc[code] = target
            print(f"[ที่พัก] {'อัปเดต' if existing else 'เพิ่มใหม่'}: {name}")
        except Exception as e:
            if not args.dry_run:
                db.rollback()
            errors.append(f"[ที่พัก] {code} ({name}): {e}")

    # ---- 2. room types (replace wholesale per accommodation) ---------------
    cleared_for = set()
    room_count = 0
    for _, row in room_df[room_df["รหัสที่พัก"].isin(TARGET_CODES)].iterrows():
        code = clean(row.get("รหัสที่พัก"))
        acc = code_to_acc.get(code)
        if not acc or args.dry_run:
            continue
        try:
            if acc.id and acc.id not in cleared_for:
                db.query(models.RoomType).filter_by(accommodation_id=acc.id).delete()
                cleared_for.add(acc.id)
            view_text = clean(row.get("วิว/ตำแหน่งห้อง")) or ""
            db.add(models.RoomType(
                accommodation_id=acc.id,
                name=clean(row.get("ชื่อห้อง/ชื่อบ้านพัก")) or "ห้องมาตรฐาน",
                price_per_night=parse_price(row.get("ราคาเริ่มต้น (บาท/คืน)")) or float(acc.price_per_night),
                max_occupancy=int(row["จำนวนผู้เข้าพักสูงสุด (คน)"]) if not pd.isna(row.get("จำนวนผู้เข้าพักสูงสุด (คน)")) else None,
                standard_occupancy=int(row["จำนวนผู้เข้าพักปกติ (คน)"]) if not pd.isna(row.get("จำนวนผู้เข้าพักปกติ (คน)")) else None,
                bed_type=clean(row.get("ประเภทและจำนวนเตียง")),
                view_type=detect_view(view_text),
                room_size_sqm=float(row["ขนาดห้อง/บ้าน (ตร.ม.)"]) if not pd.isna(row.get("ขนาดห้อง/บ้าน (ตร.ม.)")) else None,
                breakfast_included=bool(parse_yn(row.get("รวมอาหารเช้า (Y/N)"))),
                extra_bed_available=bool(parse_yn(row.get("มีเตียงเสริม (Y/N)"))),
                extra_bed_price=parse_price(row.get("ราคาเตียงเสริม (บาท/คืน)")),
                extra_bed_max=int(row["เพิ่มเตียงเสริมสูงสุด (เตียง)"]) if not pd.isna(row.get("เพิ่มเตียงเสริมสูงสุด (เตียง)")) else None,
                bedrooms=int(row["จำนวนห้องนอน"]) if not pd.isna(row.get("จำนวนห้องนอน")) else None,
                bathrooms=int(row["จำนวนห้องน้ำ"]) if not pd.isna(row.get("จำนวนห้องน้ำ")) else None,
                units_available=int(row["จำนวนห้อง/หลังที่มี"]) if not pd.isna(row.get("จำนวนห้อง/หลังที่มี")) else None,
                smoking_allowed=parse_yn(row.get("สูบบุหรี่ได้ (Y/N)")),
                pets_allowed=parse_yn(row.get("สัตว์เลี้ยงเข้าพักได้ (Y/N)")),
                description=clean(row.get("รายละเอียดห้องหรือบ้านพัก")) or clean(row.get("เงื่อนไขเพิ่มเติม")),
                sort_order=room_count,
            ))
            db.commit()
            room_count += 1
        except Exception as e:
            db.rollback()
            errors.append(f"[ประเภทห้อง] {code}: {e}")

    # ---- 3. accommodation images (replace wholesale per accommodation) ----
    img_cleared = set()
    img_count = 0
    for _, row in img_df[img_df["รหัสที่พัก"].isin(TARGET_CODES)].iterrows():
        code = clean(row.get("รหัสที่พัก"))
        acc = code_to_acc.get(code)
        url = clean(row.get("ลิงก์รูปภาพ"))
        if not acc or not url or args.dry_run:
            continue
        try:
            if acc.id and acc.id not in img_cleared:
                db.query(models.AccommodationImage).filter_by(accommodation_id=acc.id).delete()
                img_cleared.add(acc.id)
            order_raw = row.get("ลำดับการแสดง")
            db.add(models.AccommodationImage(
                accommodation_id=acc.id,
                image_url=clip(url, 500),
                image_category=clean(row.get("หมวดหมู่รูปภาพ")),
                caption=clip(clean(row.get("คำอธิบายภาพ")), 255),
                is_cover=bool(parse_yn(row.get("ใช้เป็นภาพปก (Y/N)"))),
                sort_order=int(order_raw) if not pd.isna(order_raw) else img_count,
                source_note=clip(clean(row.get("แหล่งข้อมูล/ลิงก์อ้างอิง")), 255),
                status="published",
            ))
            db.commit()
            img_count += 1
        except Exception as e:
            db.rollback()
            errors.append(f"[รูปภาพ] {code}: {e}")

    # ensure exactly one cover per accommodation that got images
    if not args.dry_run:
        for acc in code_to_acc.values():
            imgs = db.query(models.AccommodationImage).filter_by(accommodation_id=acc.id).order_by(models.AccommodationImage.sort_order).all()
            if imgs and not any(i.is_cover for i in imgs):
                imgs[0].is_cover = True
        db.commit()

    # ---- 4. POI + accommodation_places links -------------------------------
    poi_rows = poi_df.set_index("รหัสสถานที่").to_dict("index")
    link_count = 0
    for _, row in link_df[link_df["รหัสที่พัก"].isin(TARGET_CODES)].iterrows():
        code = clean(row.get("รหัสที่พัก"))
        acc = code_to_acc.get(code)
        poi_name = clean(row.get("ชื่อสถานที่สำคัญ"))
        poi_code = clean(row.get("รหัสสถานที่สำคัญ"))
        if not acc or not poi_name or args.dry_run:
            continue
        try:
            place = place_lookup.get(poi_name)
            if not place:
                poi_info = poi_rows.get(poi_code, {})
                cat_th = clean(poi_info.get("หมวดหมู่")) or clean(row.get("หมวดหมู่สถานที่")) or ""
                category = CATEGORY_MAP.get(cat_th, "attraction")
                lat = poi_info.get("ละติจูด")
                lng = poi_info.get("ลองจิจูด")
                if pd.isna(lat) or pd.isna(lng):
                    raise ValueError(f"ไม่มีพิกัดของสถานที่ '{poi_name}' ในแท็บ POI — ข้ามการเชื่อมนี้")
                district_name = clean(poi_info.get("อำเภอ"))
                district_obj = district_lookup.get(district_name)
                place = models.Place(
                    name=poi_name, category=category, latitude=float(lat), longitude=float(lng),
                    address=clean(poi_info.get("ที่อยู่")),
                    district_id=district_obj.id if district_obj else None,
                )
                db.add(place)
                db.commit()
                place_lookup[poi_name] = place

            road_km = row.get("ระยะทางตามเส้นทาง (กม.)")
            straight_km = row.get("ระยะทางเส้นตรง (กม.)")
            distance_km = road_km if not pd.isna(road_km) else straight_km
            if pd.isna(distance_km):
                continue
            travel_time = row.get("เวลาเดินทาง (นาที)")

            existing_link = db.query(models.AccommodationPlace).filter_by(accommodation_id=acc.id, place_id=place.id).first()
            link = existing_link or models.AccommodationPlace(accommodation_id=acc.id, place_id=place.id)
            link.distance_km = float(distance_km)
            link.travel_time_minutes = int(travel_time) if not pd.isna(travel_time) else None
            link.travel_method = clip(clean(row.get("วิธีเดินทาง")), 50)
            link.route_url = clip(clean(row.get("ลิงก์เส้นทาง Google Maps")), 500)
            link.note = clip(clean(row.get("เหตุผลที่ถือว่าใกล้/หมายเหตุ")), 255)
            if not existing_link:
                db.add(link)
            db.commit()
            link_count += 1
        except Exception as e:
            # a new Place (if any) was already committed above, so this
            # only rolls back the link insert itself — safe.
            db.rollback()
            errors.append(f"[สถานที่ใกล้เคียง] {code} -> {poi_name}: {e}")

    # ---- 5. reviews (append-only; external_code prevents duplicates) ------
    review_count = 0
    for _, row in review_df[review_df["รหัสที่พัก"].isin(TARGET_CODES)].iterrows():
        code = clean(row.get("รหัสที่พัก"))
        acc = code_to_acc.get(code)
        ext_code = clean(row.get("รหัสรีวิว"))
        rating = row.get("คะแนนรวม")
        if not acc or pd.isna(rating) or args.dry_run:
            continue
        try:
            if ext_code and db.query(models.Review).filter_by(external_code=ext_code).first():
                continue  # already imported on a previous run
            db.add(models.Review(
                external_code=ext_code,
                accommodation_id=acc.id,
                guest_name=clip(clean(row.get("ชื่อ/รหัสผู้รีวิว")) or "ผู้เข้าพัก", 150),
                rating=to_5_scale(rating),
                cleanliness_rating=to_5_scale(row.get("ความสะอาด")),
                location_rating=to_5_scale(row.get("ทำเล")),
                service_rating=to_5_scale(row.get("การบริการ")),
                value_rating=to_5_scale(row.get("ความคุ้มค่า")),
                comment=clean(row.get("ความคิดเห็นผู้เข้าพัก")),
            ))
            db.commit()
            review_count += 1
        except Exception as e:
            db.rollback()
            errors.append(f"[รีวิว] {code}: {e}")

    if not args.dry_run:
        db.commit()
    db.close()

    print(f"\nสรุป: ที่พัก {len(code_to_acc)} แห่ง | ห้อง {room_count} | รูปภาพ {img_count} | สถานที่ใกล้เคียง {link_count} | รีวิว {review_count}")
    if errors:
        print(f"\nพบปัญหา {len(errors)} รายการ:")
        for e in errors:
            print(f"  - {e}")

    if not args.dry_run and code_to_acc and search_index is not None:
        try:
            db2 = SessionLocal()
            count = search_index.build_index(db2)
            db2.close()
            print(f"\nอัปเดตดัชนี Semantic Search แล้ว ({count} รายการ)")
        except Exception as e:
            print(f"\nอัปเดตดัชนีไม่สำเร็จ: {e}")


if __name__ == "__main__":
    main()
