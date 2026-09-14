"""
Seeds the `places` table with real points of interest around Phitsanulok
(approximate coordinates). Distances shown on the detail page are computed
live from each accommodation's own lat/lng, so places only need entering once.

Run after schema_addendum_6.sql (or apply_addenda.py):
    python seed_places.py
"""
from app.database import SessionLocal
from app import models

# name, category, lat, lng, is_popular
PLACES = [
    ("วัดพระศรีรัตนมหาธาตุวรมหาวิหาร (วัดใหญ่)", "temple", 16.8236, 100.2656, True),
    ("วัดนางพญา", "temple", 16.8228, 100.2649, True),
    ("วัดราชบูรณะ", "temple", 16.8241, 100.2661, False),
    ("วัดอรัญญิก", "temple", 16.8180, 100.2560, False),
    ("วัดจุฬามณี", "temple", 16.7720, 100.2680, True),
    ("พิพิธภัณฑ์พื้นบ้านจ่าทวี", "museum", 16.8085, 100.2732, True),
    ("พิพิธภัณฑ์เมืองพิษณุโลก", "museum", 16.8202, 100.2668, False),
    ("หอนาฬิกาพิษณุโลก", "attraction", 16.8215, 100.2620, False),
    ("สวนชมน่านเฉลิมพระเกียรติ", "attraction", 16.8270, 100.2670, True),
    ("ถนนคนเดินพิษณุโลก (ไนท์บาซาร์)", "attraction", 16.8240, 100.2665, True),
    ("เรือนแพแม่น้ำน่าน", "attraction", 16.8258, 100.2679, False),
    ("สถานีรถไฟพิษณุโลก", "station", 16.8262, 100.2606, True),
    ("สถานีขนส่งผู้โดยสารพิษณุโลกแห่งที่ 1", "station", 16.8207, 100.2580, False),
    ("ท่าอากาศยานพิษณุโลก", "station", 16.7829, 100.2793, False),
    ("เซ็นทรัล พิษณุโลก", "mall", 16.8036, 100.2870, True),
    ("โลตัส พิษณุโลก", "mall", 16.8130, 100.2810, False),
    ("บิ๊กซี พิษณุโลก", "mall", 16.8300, 100.2730, False),
    ("เทสโก้ โลตัส ท่าทอง", "mall", 16.8380, 100.2560, False),
    ("โรงพยาบาลพุทธชินราช พิษณุโลก", "hospital", 16.8198, 100.2610, False),
    ("โรงพยาบาลพิษณุเวช", "hospital", 16.8090, 100.2790, False),
    ("โรงพยาบาลกรุงเทพพิษณุโลก", "hospital", 16.8155, 100.2720, False),
    ("ตลาดสดเทศบาล (ตลาดใต้)", "market", 16.8250, 100.2640, False),
    ("ตลาดโคกมะตูม", "market", 16.8320, 100.2560, False),
    ("ตลาดหนองบัว", "market", 16.8110, 100.2650, False),
    ("ร้านอาหารริมน่าน", "restaurant", 16.8248, 100.2672, False),
    ("ครัวคุณอ้อย พิษณุโลก", "restaurant", 16.8175, 100.2695, False),
    ("ก๋วยเตี๋ยวห้อยขาริมน่าน", "restaurant", 16.8255, 100.2668, False),
    ("7-Eleven สาขาราชดำเนิน", "convenience", 16.8225, 100.2650, False),
    ("7-Eleven สาขาบรมไตรโลกนารถ", "convenience", 16.8190, 100.2635, False),
    ("Lotus's go fresh นเรศวร", "convenience", 16.8130, 100.2705, False),
]


def run():
    db = SessionLocal()
    try:
        district = db.query(models.District).filter_by(name="เมืองพิษณุโลก").first()
        did = district.id if district else None

        existing = {p.name for p in db.query(models.Place).all()}
        added = 0
        for name, cat, lat, lng, pop in PLACES:
            if name in existing:
                continue
            db.add(models.Place(
                name=name, category=cat, latitude=lat, longitude=lng,
                is_popular=pop, district_id=did,
            ))
            added += 1
        db.commit()
        print(f"Seeded {added} places ({len(existing) + added} total).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
