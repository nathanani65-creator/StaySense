-- Run this after schema.sql, schema_addendum.sql, schema_addendum_2.sql,
-- and schema_addendum_3.sql.
--
-- Enriches room_types so the detail page can describe each accommodation
-- category the way it actually works:
--   * โรงแรม / โฮสเทล / เกสต์เฮาส์ — ห้องพัก: จุปกติกี่คน, เสริมเตียงได้ไหม
--     ราคาเสริมเตียงเท่าไร, ประเภทเตียง, ขนาดห้อง
--   * โฮมสเตย์ / รีสอร์ต (วิลล่า) — คิดเป็น "หลัง": กี่ห้องนอน กี่ห้องน้ำ
--     พักได้ทั้งหลังกี่คน มีให้บริการกี่หลัง
--
-- All columns are nullable / have safe defaults, so existing room_types
-- rows stay valid and the frontend just hides whatever isn't filled in.

ALTER TABLE room_types
  ADD COLUMN standard_occupancy  INT UNSIGNED  NULL          AFTER max_occupancy,
  ADD COLUMN extra_bed_available BOOLEAN       NOT NULL DEFAULT FALSE AFTER breakfast_included,
  ADD COLUMN extra_bed_price     DECIMAL(10,2) NULL          AFTER extra_bed_available,
  ADD COLUMN bedrooms            INT UNSIGNED  NULL          AFTER extra_bed_price,
  ADD COLUMN bathrooms           INT UNSIGNED  NULL          AFTER bedrooms,
  ADD COLUMN units_available     INT UNSIGNED  NULL          AFTER bathrooms,
  ADD COLUMN description         VARCHAR(255)  NULL          AFTER units_available;
