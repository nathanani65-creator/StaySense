-- Run this after schema.sql (or fold it into schema.sql before first deploy).
-- Adds a lightweight free-form tags column used to render the small pill
-- tags on the frontend card (e.g. ["วิวแม่น้ำ", "เงียบสงบ"]), separate from
-- the structured amenities relation.

ALTER TABLE accommodations
  ADD COLUMN tags_json JSON NULL AFTER recommended_reason;
