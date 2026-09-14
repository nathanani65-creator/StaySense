-- Run after schema_addendum_5.sql (or: python apply_addenda.py).
--
-- Points of interest used by the accommodation detail page's right rail
-- ("ที่เที่ยวยอดนิยม" / "สถานที่ใกล้ที่สุด"). Distances are NOT stored — they
-- are computed at query time with the haversine formula from each
-- accommodation's own latitude/longitude, so a place only has to be entered
-- once with its real coordinates.

CREATE TABLE places (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(200) NOT NULL,
  category    VARCHAR(30)  NOT NULL,   -- 'temple' | 'attraction' | 'station' | 'mall'
                                       -- | 'hospital' | 'market' | 'convenience' | 'restaurant' | 'museum'
  latitude    DECIMAL(10,7) NOT NULL,
  longitude   DECIMAL(10,7) NOT NULL,
  is_popular  BOOLEAN NOT NULL DEFAULT FALSE,  -- surface in "ที่เที่ยวยอดนิยม"
  district_id INT UNSIGNED NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_place_district
    FOREIGN KEY (district_id) REFERENCES districts(id)
    ON UPDATE CASCADE ON DELETE SET NULL,

  KEY idx_place_category (category),
  KEY idx_place_popular (is_popular)
) ENGINE=InnoDB;
