-- Run after schema_addendum_13.sql (or: python apply_addenda.py).
--
-- Supports importing the real data-collection spreadsheet
-- (staysense_data_collection.xlsx) into the database:
--
--  1. external_code columns let the importer be re-run safely — each row
--     carries the spreadsheet's own stable code (HT001, UNIT001, POI001,
--     IMG001, REV001, NEAR001) so a re-import upserts instead of duplicating.
--  2. reviews.user_id becomes nullable + reviews.guest_name is added, so a
--     review collected from an external source (e.g. Agoda) can be stored
--     honestly under the reviewer's real name without inventing a fake
--     StaySense member account for them.
--  3. accommodation_places is a new curated join table: the spreadsheet's
--     "ที่พักใกล้สถานที่สำคัญ" sheet has real, manually-verified
--     distance/travel-time/travel-method data per accommodation-place pair,
--     which is more accurate than the pure-haversine straight-line distance
--     crud.nearby_places() falls back to for everything else.

ALTER TABLE accommodations
  ADD COLUMN external_code VARCHAR(30) NULL UNIQUE AFTER id;

ALTER TABLE room_types
  ADD COLUMN external_code VARCHAR(30) NULL UNIQUE AFTER id;

ALTER TABLE places
  ADD COLUMN external_code VARCHAR(30) NULL UNIQUE AFTER id;

ALTER TABLE accommodation_images
  ADD COLUMN external_code VARCHAR(30) NULL UNIQUE AFTER id;

ALTER TABLE reviews
  MODIFY COLUMN user_id INT UNSIGNED NULL,
  ADD COLUMN guest_name VARCHAR(150) NULL AFTER user_id,
  ADD COLUMN external_code VARCHAR(30) NULL UNIQUE AFTER guest_name;

CREATE TABLE IF NOT EXISTS accommodation_places (
  id                   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  accommodation_id     INT UNSIGNED NOT NULL,
  place_id             INT UNSIGNED NOT NULL,
  distance_km          DECIMAL(6,2) NULL,
  travel_time_minutes  INT UNSIGNED NULL,
  travel_method        VARCHAR(50) NULL,
  note                 VARCHAR(255) NULL,
  route_url            VARCHAR(500) NULL,
  source_note          VARCHAR(255) NULL,
  verified_at          DATE NULL,
  external_code        VARCHAR(30) NULL UNIQUE,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uq_accommodation_place (accommodation_id, place_id),
  CONSTRAINT fk_accplace_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_accplace_place
    FOREIGN KEY (place_id) REFERENCES places(id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;
