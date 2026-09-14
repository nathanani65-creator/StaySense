"""
Imports real accommodation data from the filled-in Excel template
(staysense_data_collection_template.xlsx) into MySQL. Reads two sheets:
  - "ที่พัก"       — core accommodation fields + policies
  - "ประเภทห้อง"   — room types, linked back to "ที่พัก" by exact name match

Usage:
    python import_accommodations.py path/to/filled_template.xlsx
    python import_accommodations.py path/to/filled_template.xlsx --clear-mock

--clear-mock deletes ALL existing accommodations first. Use this exactly
once, the first time you switch from the 48 seeded mock hotels to real data.
Do not use it on later re-imports, or you will lose real rows added by hand
through the API/admin tools since the last import.

Safe to re-run: matching is done on (name, district) for accommodations and
on accommodation name for room types, so fixing a typo in the sheet and
re-running updates the existing rows instead of duplicating them.
"""
import argparse
import sys

import pandas as pd

from app.database import SessionLocal
from app import models

try:
    from app.semantic import index as search_index
except Exception:  # pragma: no cover - semantic deps are optional at import time
    search_index = None


REQUIRED_COLUMNS = [
    "ชื่อที่พัก", "ประเภท", "อำเภอ", "ที่อยู่", "ละติจูด", "ลองจิจูด",
    "ราคาต่อคืน (บาท)", "เบอร์โทร", "สิ่งอำนวยความสะดวก (รหัส, คั่นด้วย ,)",
    "คำอธิบาย (สำหรับ Semantic Search)", "ลิงก์รูปภาพ",
]
ROOM_TYPE_SHEET = "ประเภทห้อง"
ROOM_TYPE_REQUIRED_COLUMNS = [
    "ชื่อที่พัก (ต้องตรงกับแท็บ \"ที่พัก\" เป๊ะ)", "ชื่อประเภทห้อง", "ราคาต่อคืน (บาท)",
]


def clean(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if text.lower() in ("nan", "none", ""):
        return default
    return text


def parse_yn(value):
    """'Y'/'N' dropdown -> True/False/None (None = left blank)."""
    text = clean(value).strip().upper()
    if text == "Y":
        return True
    if text == "N":
        return False
    return None


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("excel_path", help="path to the filled-in .xlsx template")
    p.add_argument("--sheet", default="ที่พัก", help="accommodations sheet name (default: ที่พัก)")
    p.add_argument("--clear-mock", action="store_true", help="delete ALL existing accommodations first")
    p.add_argument("--dry-run", action="store_true", help="validate and report only, write nothing to the database")
    return p.parse_args()


def import_accommodations(db, df, dry_run):
    type_lookup = {t.name_th: t for t in db.query(models.AccommodationType).all()}
    district_lookup = {d.name: d for d in db.query(models.District).all()}
    amenity_lookup = {a.code: a for a in db.query(models.Amenity).all()}

    imported, updated, skipped_examples, errors = 0, 0, 0, []
    name_to_accommodation = {}  # for linking room types afterwards

    for idx, row in df.iterrows():
        excel_row_num = idx + 2  # header is row 1
        name = clean(row.get("ชื่อที่พัก"))
        if not name:
            continue  # blank row, ignore silently
        if "(ตัวอย่าง)" in name:
            skipped_examples += 1
            continue

        try:
            type_name = clean(row.get("ประเภท"))
            district_name = clean(row.get("อำเภอ"))
            type_obj = type_lookup.get(type_name)
            district_obj = district_lookup.get(district_name)
            if not type_obj:
                raise ValueError(f"ไม่รู้จักประเภท '{type_name}' (ต้องเลือกจาก dropdown เท่านั้น)")
            if not district_obj:
                raise ValueError(f"ไม่รู้จักอำเภอ '{district_name}' (ต้องเลือกจาก dropdown เท่านั้น)")

            lat_raw = row.get("ละติจูด")
            lng_raw = row.get("ลองจิจูด")
            price_raw = row.get("ราคาต่อคืน (บาท)")
            if pd.isna(lat_raw) or pd.isna(lng_raw):
                raise ValueError("ไม่มีพิกัดละติจูด/ลองจิจูด")
            if pd.isna(price_raw):
                raise ValueError("ไม่มีราคาต่อคืน")
            latitude = float(lat_raw)
            longitude = float(lng_raw)
            price = float(price_raw)

            amenity_codes = [c.strip() for c in clean(row.get("สิ่งอำนวยความสะดวก (รหัส, คั่นด้วย ,)")).split(",") if c.strip()]
            amenity_objs = []
            for code in amenity_codes:
                a = amenity_lookup.get(code)
                if not a:
                    raise ValueError(f"ไม่รู้จักรหัสสิ่งอำนวยความสะดวก '{code}' "
                                      f"(ใช้ได้เฉพาะ: {', '.join(amenity_lookup.keys())})")
                amenity_objs.append(a)

            image_url = clean(row.get("ลิงก์รูปภาพ"))

            # policies (all optional)
            checkin_time = clean(row.get("เวลาเช็กอิน")) or None
            checkout_time = clean(row.get("เวลาเช็กเอาต์")) or None
            cancellation_policy = clean(row.get("นโยบายยกเลิก/คืนเงิน")) or None
            min_age_raw = row.get("อายุขั้นต่ำผู้เช็กอิน (ปี)")
            min_age = int(min_age_raw) if not pd.isna(min_age_raw) else None
            smoking_allowed = parse_yn(row.get("สูบบุหรี่ได้ไหม (Y/N)"))
            deposit_required = bool(parse_yn(row.get("ต้องมัดจำไหม (Y/N)")))
            deposit_note = clean(row.get("รายละเอียดมัดจำ")) or None
            payment_methods = [m.strip() for m in clean(row.get("วิธีชำระเงิน (คั่นด้วย ,)")).split(",") if m.strip()]

            # pricing conditions (schema_addendum_5, all optional)
            deposit_amount_raw = row.get("จำนวนเงินมัดจำ (บาท)")
            deposit_amount = float(deposit_amount_raw) if not pd.isna(deposit_amount_raw) else None
            deposit_percent_raw = row.get("มัดจำ (% ของยอดจอง)")
            deposit_percent = int(deposit_percent_raw) if not pd.isna(deposit_percent_raw) else None
            advance_booking_required = bool(parse_yn(row.get("ต้องจองล่วงหน้าไหม (Y/N)")))
            advance_days_raw = row.get("ต้องจองล่วงหน้ากี่วัน")
            advance_booking_days = int(advance_days_raw) if not pd.isna(advance_days_raw) else None
            price_conditions = clean(row.get("เงื่อนไขราคาเพิ่มเติม")) or None

            # contact channels (schema_addendum_5, all optional)
            contact_line = clean(row.get("LINE ID / ลิงก์ LINE")) or None
            contact_facebook = clean(row.get("Facebook (ลิงก์หรือชื่อเพจ)")) or None
            contact_instagram = clean(row.get("Instagram (@ หรือ ลิงก์)")) or None
            website_url = clean(row.get("เว็บไซต์")) or None
            google_maps_url = clean(row.get("ลิงก์ Google Maps")) or None

            if dry_run:
                imported += 1
                continue

            existing = (
                db.query(models.Accommodation)
                .filter_by(name=name, district_id=district_obj.id)
                .first()
            )
            target = existing or models.Accommodation(name=name, district_id=district_obj.id)

            target.type_id = type_obj.id
            target.address = clean(row.get("ที่อยู่"))
            target.latitude = latitude
            target.longitude = longitude
            target.price_per_night = price
            target.phone = clean(row.get("เบอร์โทร"))
            target.description = clean(row.get("คำอธิบาย (สำหรับ Semantic Search)"))
            target.amenities = amenity_objs
            if image_url:
                target.images = [models.AccommodationImage(image_url=image_url, is_cover=True)]
            target.checkin_time = checkin_time
            target.checkout_time = checkout_time
            target.cancellation_policy = cancellation_policy
            target.min_age = min_age
            target.smoking_allowed = smoking_allowed
            target.deposit_required = deposit_required
            target.deposit_note = deposit_note
            target.deposit_amount = deposit_amount
            target.deposit_percent = deposit_percent
            target.advance_booking_required = advance_booking_required
            target.advance_booking_days = advance_booking_days
            target.price_conditions = price_conditions
            target.payment_methods_json = payment_methods or None
            target.contact_line = contact_line
            target.contact_facebook = contact_facebook
            target.contact_instagram = contact_instagram
            target.website_url = website_url
            target.google_maps_url = google_maps_url

            if not existing:
                db.add(target)
                db.flush()  # get target.id before room-type linking
            name_to_accommodation[name] = target

            if existing:
                updated += 1
            else:
                imported += 1

        except Exception as e:
            errors.append(f"[ที่พัก] แถวที่ {excel_row_num} ('{name}'): {e}")

    return imported, updated, skipped_examples, errors, name_to_accommodation


def import_room_types(db, df, name_to_accommodation, dry_run):
    imported, cleared_for, errors = 0, set(), []
    name_col = ROOM_TYPE_REQUIRED_COLUMNS[0]

    for idx, row in df.iterrows():
        excel_row_num = idx + 2
        acc_name = clean(row.get(name_col))
        if not acc_name:
            continue
        if "(ตัวอย่าง)" in acc_name:
            continue

        try:
            acc = name_to_accommodation.get(acc_name)
            if not acc:
                raise ValueError(
                    f"ไม่พบที่พักชื่อ '{acc_name}' ในแท็บ \"ที่พัก\" "
                    f"(ชื่อต้องตรงกันเป๊ะทุกตัวอักษร รวมช่องว่าง)"
                )

            room_name = clean(row.get("ชื่อประเภทห้อง"))
            price_raw = row.get("ราคาต่อคืน (บาท)")
            if not room_name:
                raise ValueError("ไม่มีชื่อประเภทห้อง")
            if pd.isna(price_raw):
                raise ValueError("ไม่มีราคาต่อคืนของห้องนี้")

            max_occ_raw = row.get("จำนวนผู้เข้าพักสูงสุด (คน)")
            std_occ_raw = row.get("จำนวนผู้เข้าพักปกติ ไม่เสริมเตียง (คน)")
            size_raw = row.get("ขนาดห้อง (ตร.ม.)")
            extra_bed_price_raw = row.get("ราคาเสริมเตียง (บาท/คืน)")
            bedrooms_raw = row.get("จำนวนห้องนอน (สำหรับโฮมสเตย์/วิลล่า)")
            bathrooms_raw = row.get("จำนวนห้องน้ำ (สำหรับโฮมสเตย์/วิลล่า)")
            units_raw = row.get("มีห้อง/หลังประเภทนี้กี่ยูนิต")

            if dry_run:
                imported += 1
                continue

            # first time we see this accommodation in the sheet: replace its
            # room types wholesale, so re-running after edits doesn't pile up duplicates
            if acc.id not in cleared_for:
                db.query(models.RoomType).filter_by(accommodation_id=acc.id).delete()
                cleared_for.add(acc.id)

            extra_bed_price = float(extra_bed_price_raw) if not pd.isna(extra_bed_price_raw) else None
            db.add(models.RoomType(
                accommodation_id=acc.id,
                name=room_name,
                price_per_night=float(price_raw),
                max_occupancy=int(max_occ_raw) if not pd.isna(max_occ_raw) else None,
                standard_occupancy=int(std_occ_raw) if not pd.isna(std_occ_raw) else None,
                bed_type=clean(row.get("ประเภทเตียง")) or None,
                room_size_sqm=float(size_raw) if not pd.isna(size_raw) else None,
                breakfast_included=bool(parse_yn(row.get("รวมอาหารเช้าไหม (Y/N)"))),
                # เสริมเตียงได้ไหม: ดูจากคอลัมน์ Y/N ก่อน ถ้าเว้นว่างแต่กรอกราคาเสริมเตียงมา ก็ถือว่าได้
                extra_bed_available=bool(parse_yn(row.get("เสริมเตียงได้ไหม (Y/N)"))) or extra_bed_price is not None,
                extra_bed_price=extra_bed_price,
                bedrooms=int(bedrooms_raw) if not pd.isna(bedrooms_raw) else None,
                bathrooms=int(bathrooms_raw) if not pd.isna(bathrooms_raw) else None,
                units_available=int(units_raw) if not pd.isna(units_raw) else None,
                description=clean(row.get("รายละเอียดเพิ่มเติมของห้อง/หลัง")) or None,
                sort_order=imported,
            ))
            imported += 1

        except Exception as e:
            errors.append(f"[ประเภทห้อง] แถวที่ {excel_row_num} ('{acc_name}'): {e}")

    return imported, errors


def main():
    args = parse_args()

    try:
        df = pd.read_excel(args.excel_path, sheet_name=args.sheet)
    except Exception as e:
        print(f"เปิดไฟล์ไม่สำเร็จ: {e}")
        sys.exit(1)

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        print("ไฟล์นี้ไม่ใช่ template ที่ถูกต้อง ขาดคอลัมน์ในแท็บ \"ที่พัก\":")
        for c in missing_cols:
            print(f"  - {c}")
        sys.exit(1)

    room_df = None
    try:
        room_df = pd.read_excel(args.excel_path, sheet_name=ROOM_TYPE_SHEET)
        missing_room_cols = [c for c in ROOM_TYPE_REQUIRED_COLUMNS if c not in room_df.columns]
        if missing_room_cols:
            print(f"แท็บ \"{ROOM_TYPE_SHEET}\" มีอยู่แต่ขาดคอลัมน์ที่จำเป็น — ข้ามการนำเข้าประเภทห้อง")
            room_df = None
    except Exception:
        print(f"ไม่พบแท็บ \"{ROOM_TYPE_SHEET}\" ในไฟล์นี้ — ข้ามการนำเข้าประเภทห้อง (ใช้ไฟล์เก่าอยู่ก็ปกติ)")

    db = SessionLocal()

    if args.clear_mock and not args.dry_run:
        count = db.query(models.Accommodation).delete()
        db.commit()
        print(f"ลบข้อมูลเดิม {count} รายการ (--clear-mock)\n")

    imported, updated, skipped_examples, errors, name_to_accommodation = import_accommodations(db, df, args.dry_run)

    room_imported, room_errors = 0, []
    if room_df is not None:
        room_imported, room_errors = import_room_types(db, room_df, name_to_accommodation, args.dry_run)
        errors += room_errors

    if not args.dry_run:
        db.commit()
    db.close()

    print(f"ที่พัก — นำเข้าใหม่: {imported} แห่ง | อัปเดตของเดิม: {updated} แห่ง | ข้ามแถวตัวอย่าง: {skipped_examples} แถว")
    if room_df is not None:
        print(f"ประเภทห้อง — นำเข้า/แทนที่แล้ว: {room_imported} แถว")
    if args.dry_run:
        print("(โหมด --dry-run: ยังไม่ได้บันทึกอะไรลงฐานข้อมูลจริง)")

    if errors:
        print(f"\nพบปัญหา {len(errors)} รายการ ต้องแก้ในชีตแล้วรันใหม่:")
        for e in errors:
            print(f"  - {e}")

    if not args.dry_run and (imported or updated) and search_index is not None:
        try:
            db2 = SessionLocal()
            count = search_index.build_index(db2)
            db2.close()
            print(f"\nอัปเดตดัชนี Semantic Search แล้ว ({count} รายการ)")
        except Exception as e:
            print(f"\nอัปเดตดัชนี Semantic Search ไม่สำเร็จ (ไม่กระทบข้อมูลที่นำเข้าไปแล้ว): {e}")


if __name__ == "__main__":
    main()
