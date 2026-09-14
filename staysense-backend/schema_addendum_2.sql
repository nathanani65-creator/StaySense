-- Run this after schema.sql and schema_addendum.sql.
-- Expands the amenities reference table from 6 to 16 codes so the detail
-- page can group them into clear categories (ภายในห้อง / ภายในที่พัก /
-- บริการ / ที่จอดรถและการเดินทาง / การรองรับพิเศษ) instead of one flat list.
-- No structural change needed — accommodation_amenities is already a
-- many-to-many join, so these are just new rows.

INSERT INTO amenities (code, label_th, icon_key) VALUES
  ('aircon',       'เครื่องปรับอากาศ',        'aircon'),
  ('tv',           'โทรทัศน์',                'tv'),
  ('fridge',       'ตู้เย็น',                 'fridge'),
  ('water_heater', 'เครื่องทำน้ำอุ่น',        'water_heater'),
  ('restaurant',   'ร้านอาหาร',               'restaurant'),
  ('gym',          'ฟิตเนส',                  'gym'),
  ('elevator',     'ลิฟต์',                   'elevator'),
  ('laundry',      'บริการซักรีด',            'laundry'),
  ('reception24',  'แผนกต้อนรับ 24 ชม.',      'reception'),
  ('wheelchair',   'รองรับผู้ใช้รถเข็น',      'wheelchair'),
  ('elderly',      'เหมาะสำหรับผู้สูงอายุ',   'elderly')
ON DUPLICATE KEY UPDATE label_th = VALUES(label_th);

-- Clarify that "pet" may carry conditions/extra fees, per the request to
-- not leave that ambiguous on the detail page.
UPDATE amenities SET label_th = 'สัตว์เลี้ยงเข้าพักได้ (มีเงื่อนไข)' WHERE code = 'pet';
UPDATE amenities SET label_th = 'ห้องสำหรับครอบครัว/เด็ก' WHERE code = 'family';
