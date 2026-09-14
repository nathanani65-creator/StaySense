-- Run this after schema.sql, schema_addendum.sql, and schema_addendum_2.sql.
-- Adds:
--   1. room_types — multiple priced room categories per accommodation
--   2. policy fields on accommodations (check-in/out, cancellation, age,
--      smoking, deposit, payment methods)
--   3. per-category rating averages on accommodations (cleanliness/location/
--      service/value), maintained by triggers exactly like rating_avg
--      already is — never hand-set these, they're always derived from real
--      review rows, same "no fabricated numbers" principle as rating_avg.
--   4. per-category scores on reviews themselves (nullable — a review can
--      still be overall-only)

-- ------------------------------------------------------------
-- 1. Room types
-- ------------------------------------------------------------
CREATE TABLE room_types (
  id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  accommodation_id    INT UNSIGNED NOT NULL,
  name                VARCHAR(100) NOT NULL,        -- 'Standard' | 'Deluxe' | 'Family' ...
  price_per_night     DECIMAL(10,2) NOT NULL,
  max_occupancy       INT UNSIGNED,
  bed_type            VARCHAR(100),                 -- 'เตียงคู่ 1 เตียง' | 'เตียงเดี่ยว 2 เตียง' ...
  room_size_sqm       DECIMAL(6,1),
  breakfast_included  BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order          INT UNSIGNED NOT NULL DEFAULT 0,

  CONSTRAINT fk_room_type_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  KEY idx_room_type_accommodation (accommodation_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2 & 3. Policy fields + category rating averages on accommodations
-- ------------------------------------------------------------
ALTER TABLE accommodations
  ADD COLUMN checkin_time         VARCHAR(20)   NULL AFTER recommended_reason,
  ADD COLUMN checkout_time        VARCHAR(20)   NULL AFTER checkin_time,
  ADD COLUMN cancellation_policy  TEXT          NULL AFTER checkout_time,
  ADD COLUMN min_age              INT UNSIGNED  NULL AFTER cancellation_policy,
  ADD COLUMN smoking_allowed      BOOLEAN       NULL AFTER min_age,
  ADD COLUMN deposit_required     BOOLEAN       NOT NULL DEFAULT FALSE AFTER smoking_allowed,
  ADD COLUMN deposit_note         VARCHAR(255)  NULL AFTER deposit_required,
  ADD COLUMN payment_methods_json JSON          NULL AFTER deposit_note,
  ADD COLUMN rating_cleanliness   DECIMAL(2,1)  NOT NULL DEFAULT 0 AFTER rating_avg,
  ADD COLUMN rating_location      DECIMAL(2,1)  NOT NULL DEFAULT 0 AFTER rating_cleanliness,
  ADD COLUMN rating_service       DECIMAL(2,1)  NOT NULL DEFAULT 0 AFTER rating_location,
  ADD COLUMN rating_value         DECIMAL(2,1)  NOT NULL DEFAULT 0 AFTER rating_service;

-- ------------------------------------------------------------
-- 4. Per-category scores on individual reviews
-- ------------------------------------------------------------
ALTER TABLE reviews
  ADD COLUMN cleanliness_rating TINYINT UNSIGNED NULL AFTER rating,
  ADD COLUMN location_rating    TINYINT UNSIGNED NULL AFTER cleanliness_rating,
  ADD COLUMN service_rating     TINYINT UNSIGNED NULL AFTER location_rating,
  ADD COLUMN value_rating       TINYINT UNSIGNED NULL AFTER service_rating;

-- ------------------------------------------------------------
-- Replace the review triggers so they also maintain the 4 category averages
-- ------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_reviews_after_insert;
DROP TRIGGER IF EXISTS trg_reviews_after_update;
DROP TRIGGER IF EXISTS trg_reviews_after_delete;

DELIMITER $$

CREATE TRIGGER trg_reviews_after_insert
AFTER INSERT ON reviews
FOR EACH ROW
BEGIN
  UPDATE accommodations a
  SET review_count      = (SELECT COUNT(*) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_avg         = (SELECT ROUND(AVG(rating),1) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_cleanliness = (SELECT IFNULL(ROUND(AVG(cleanliness_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_location    = (SELECT IFNULL(ROUND(AVG(location_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_service     = (SELECT IFNULL(ROUND(AVG(service_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_value       = (SELECT IFNULL(ROUND(AVG(value_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id)
  WHERE a.id = NEW.accommodation_id;
END$$

CREATE TRIGGER trg_reviews_after_update
AFTER UPDATE ON reviews
FOR EACH ROW
BEGIN
  UPDATE accommodations a
  SET review_count      = (SELECT COUNT(*) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_avg         = (SELECT ROUND(AVG(rating),1) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_cleanliness = (SELECT IFNULL(ROUND(AVG(cleanliness_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_location    = (SELECT IFNULL(ROUND(AVG(location_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_service     = (SELECT IFNULL(ROUND(AVG(service_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_value       = (SELECT IFNULL(ROUND(AVG(value_rating),1),0) FROM reviews WHERE accommodation_id = NEW.accommodation_id)
  WHERE a.id = NEW.accommodation_id;
END$$

CREATE TRIGGER trg_reviews_after_delete
AFTER DELETE ON reviews
FOR EACH ROW
BEGIN
  UPDATE accommodations a
  SET review_count      = (SELECT COUNT(*) FROM reviews WHERE accommodation_id = OLD.accommodation_id),
      rating_avg         = (SELECT IFNULL(ROUND(AVG(rating),1),0) FROM reviews WHERE accommodation_id = OLD.accommodation_id),
      rating_cleanliness = (SELECT IFNULL(ROUND(AVG(cleanliness_rating),1),0) FROM reviews WHERE accommodation_id = OLD.accommodation_id),
      rating_location    = (SELECT IFNULL(ROUND(AVG(location_rating),1),0) FROM reviews WHERE accommodation_id = OLD.accommodation_id),
      rating_service     = (SELECT IFNULL(ROUND(AVG(service_rating),1),0) FROM reviews WHERE accommodation_id = OLD.accommodation_id),
      rating_value       = (SELECT IFNULL(ROUND(AVG(value_rating),1),0) FROM reviews WHERE accommodation_id = OLD.accommodation_id)
  WHERE a.id = OLD.accommodation_id;
END$$

DELIMITER ;
