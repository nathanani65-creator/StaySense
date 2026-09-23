"""
One-off repair for Place rows that were created with the wrong
category/coordinates because their accommodation_places link row cited a
POI code shifted by one relative to its own name/category columns (see the
comment in import_new_template.py's POI section). Re-derives the correct
category/lat/lng/address from the POI sheet by NAME (which is internally
consistent) and updates the existing Place row in place — no accommodation
or accommodation_places rows are touched.

Usage:
    python fix_poi_category_shift.py "path/to/file.xlsx" [--dry-run]
"""
import argparse

import pandas as pd

from app.database import SessionLocal
from app import models

CATEGORY_MAP = {
    "วัด": "temple", "ศาสนสถาน": "temple",
    "ห้างสรรพสินค้า": "mall", "ศูนย์การค้า": "mall", "ห้างค้าปลีก-ค้าส่งขนาดใหญ่": "mall",
    "โรงพยาบาล": "hospital",
    "สถานีรถไฟ": "station", "สถานีขนส่ง": "station",
    "ร้านอาหาร": "restaurant",
    "ร้านสะดวกซื้อ": "convenience",
    "ตลาด": "market",
    "มหาวิทยาลัย": "university", "สถานศึกษา": "university",
    "สถานบันเทิง": "nightlife",
    "แหล่งท่องเที่ยว": "attraction", "สถานที่ท่องเที่ยว": "attraction",
    "พิพิธภัณฑ์": "museum",
    "สนามบิน": "airport",
}

# Names known (from the Sep 2026 audit) to have been created with the wrong
# category and/or coordinates by the pre-fix importer.
TARGET_NAMES = {
    "ตลาดสดเทศบาลตำบลป่าแดง",
    "สถานีรถไฟบางกระทุ่ม",
    "ร้านกล้วยตาก จิราพร",
    "วัดห้วยแก้ว",
    "ครัวระหาน",
    "วัดจันทร์ตะวันตก",
    "มหาวิทยาลัยนเรศวร",
    "โรงพยาบาลมหาวิทยาลัยนเรศวร",
    "โรงพยาบาลพุทธชินราช  พิษณุโลก",
    "นามุงคาเฟ่ ณ บ้านมุง",
    "เขื่อนนเรศวร",
    "วัดจุฬามณี",
    "George's Pizza",
}

TH_LAT_RANGE = (5.0, 21.0)
TH_LNG_RANGE = (97.0, 106.0)


def coords_plausible(lat, lng):
    """Same class of copy-paste mistake as the accommodation-level check in
    import_new_template.py — catches a latitude value pasted into the
    longitude column too (e.g. George's Pizza's own POI row has lat=lng=
    17.027 in the source sheet itself, not just in a shifted link row)."""
    if lat is None or lng is None:
        return False
    lat, lng = float(lat), float(lng)
    if abs(lat - lng) < 1e-6:
        return False
    return TH_LAT_RANGE[0] <= lat <= TH_LAT_RANGE[1] and TH_LNG_RANGE[0] <= lng <= TH_LNG_RANGE[1]


def clean(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("excel_path")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    poi_df = pd.read_excel(args.excel_path, sheet_name="สถานที่สำคัญ (POI)")

    db = SessionLocal()
    district_lookup = {d.name: d for d in db.query(models.District).all()}

    for _, row in poi_df.iterrows():
        name = clean(row.get("ชื่อสถานที่"))
        if name not in TARGET_NAMES:
            continue
        place = db.query(models.Place).filter_by(name=name).first()
        if not place:
            print(f"ไม่พบ Place '{name}' ในฐานข้อมูล — ข้าม")
            continue

        cat_th = clean(row.get("หมวดหมู่")) or ""
        category = CATEGORY_MAP.get(cat_th, "attraction")
        lat, lng = row.get("ละติจูด"), row.get("ลองจิจูด")
        address = clean(row.get("ที่อยู่"))
        district_name = clean(row.get("อำเภอ"))
        district_obj = district_lookup.get(district_name)

        before = (place.category, float(place.latitude), float(place.longitude))
        if coords_plausible(lat, lng):
            after = (category, float(lat), float(lng))
        else:
            print(f"  !! '{name}' — พิกัดต้นทาง ({lat}, {lng}) ผิดปกติ (ในชีต POI เองก็ผิด ไม่ใช่แค่ลิงก์เพี้ยน) คงพิกัดเดิมไว้ ต้องแก้ที่ชีตต้นฉบับแล้วรันใหม่")
            after = (category, before[1], before[2])
        print(f"{name}: category {before[0]!r} -> {after[0]!r}, lat/lng {before[1:]} -> {after[1:]}")

        if not args.dry_run:
            place.category = category
            place.latitude = after[1]
            place.longitude = after[2]
            place.address = address
            place.district_id = district_obj.id if district_obj else place.district_id
            db.commit()

    db.close()


if __name__ == "__main__":
    main()
