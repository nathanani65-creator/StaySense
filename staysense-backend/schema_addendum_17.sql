-- Nearby ("ใกล้ฉัน") location search: search-log metadata only.
-- Deliberately no latitude/longitude columns — anonymous coordinates are
-- session-only on the frontend, and logged-in search history intentionally
-- never stores precise coordinates (see StaySense home/nearby-search spec).

ALTER TABLE search_logs ADD COLUMN accommodation_type VARCHAR(30) NULL;
ALTER TABLE search_logs ADD COLUMN facilities_json JSON NULL;
ALTER TABLE search_logs ADD COLUMN radius_km DECIMAL(5,2) NULL;
ALTER TABLE search_logs ADD COLUMN sort_by VARCHAR(20) NULL;
ALTER TABLE search_logs ADD COLUMN use_current_location BOOLEAN NOT NULL DEFAULT FALSE;
