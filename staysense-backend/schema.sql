-- ============================================================
-- StaySense Phitsanulok — MySQL Schema
-- ============================================================
-- Engine/charset chosen for Thai text support
SET NAMES utf8mb4;
SET default_storage_engine = InnoDB;

CREATE DATABASE IF NOT EXISTS staysense_phitsanulok
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE staysense_phitsanulok;

-- ------------------------------------------------------------
-- 1. Reference tables
-- ------------------------------------------------------------

CREATE TABLE districts (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(100) NOT NULL,           -- e.g. 'เมืองพิษณุโลก'
  province      VARCHAR(100) NOT NULL DEFAULT 'พิษณุโลก',
  landmark_name VARCHAR(150),                     -- headline landmark, e.g. 'วัดพระศรีรัตนมหาธาตุฯ'
  center_lat    DECIMAL(10,7),                     -- used to render the district pin on the map
  center_lng    DECIMAL(10,7),
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_districts_name (name)
) ENGINE=InnoDB;

CREATE TABLE accommodation_types (
  id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  code     VARCHAR(30) NOT NULL,                  -- 'hotel' | 'resort' | 'homestay' | 'hostel' | 'guesthouse'
  name_th  VARCHAR(100) NOT NULL,                 -- 'โรงแรม', 'รีสอร์ต', ...
  icon_key VARCHAR(50),
  UNIQUE KEY uq_types_code (code)
) ENGINE=InnoDB;

CREATE TABLE amenities (
  id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  code     VARCHAR(30) NOT NULL,                  -- 'wifi' | 'parking' | 'breakfast' | 'pool' | 'family' | 'pet'
  label_th VARCHAR(100) NOT NULL,
  icon_key VARCHAR(50),
  UNIQUE KEY uq_amenities_code (code)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. Core entity: accommodations
-- ------------------------------------------------------------

CREATE TABLE accommodations (
  id                    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name                  VARCHAR(200) NOT NULL,
  type_id               INT UNSIGNED NOT NULL,
  district_id           INT UNSIGNED NOT NULL,
  description           TEXT,                     -- free-text used to build the semantic embedding
  address               VARCHAR(255),
  latitude              DECIMAL(10,7),
  longitude             DECIMAL(10,7),
  price_per_night       DECIMAL(10,2) NOT NULL,
  landmark_distance_km  DECIMAL(5,2),              -- distance to district.landmark_name, for display
  phone                 VARCHAR(20),
  -- denormalized for fast listing/sorting; kept in sync by the triggers below
  rating_avg            DECIMAL(2,1) NOT NULL DEFAULT 0,
  review_count          INT UNSIGNED NOT NULL DEFAULT 0,
  recommended_reason    VARCHAR(255),              -- admin-curated "เหตุผลที่แนะนำ" text shown on the card
  status                ENUM('active','inactive') NOT NULL DEFAULT 'active',
  created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_acc_type
    FOREIGN KEY (type_id) REFERENCES accommodation_types(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_acc_district
    FOREIGN KEY (district_id) REFERENCES districts(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,

  KEY idx_acc_type (type_id),
  KEY idx_acc_district (district_id),
  KEY idx_acc_price (price_per_night),
  KEY idx_acc_rating (rating_avg),
  KEY idx_acc_status (status)
) ENGINE=InnoDB;

CREATE TABLE accommodation_images (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  accommodation_id INT UNSIGNED NOT NULL,
  image_url        VARCHAR(500) NOT NULL,
  sort_order       INT UNSIGNED NOT NULL DEFAULT 0,
  is_cover         BOOLEAN NOT NULL DEFAULT FALSE,

  CONSTRAINT fk_img_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  KEY idx_img_accommodation (accommodation_id)
) ENGINE=InnoDB;

-- many-to-many: an accommodation can have many amenities, an amenity applies to many accommodations
CREATE TABLE accommodation_amenities (
  accommodation_id INT UNSIGNED NOT NULL,
  amenity_id       INT UNSIGNED NOT NULL,
  PRIMARY KEY (accommodation_id, amenity_id),

  CONSTRAINT fk_aa_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_aa_amenity
    FOREIGN KEY (amenity_id) REFERENCES amenities(id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 3. Users, favorites, reviews
-- ------------------------------------------------------------

CREATE TABLE users (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  email         VARCHAR(150) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('user','admin') NOT NULL DEFAULT 'user',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE favorites (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id          INT UNSIGNED NOT NULL,
  accommodation_id INT UNSIGNED NOT NULL,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_fav_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_fav_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_fav_user_acc (user_id, accommodation_id)
) ENGINE=InnoDB;

CREATE TABLE reviews (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  accommodation_id INT UNSIGNED NOT NULL,
  user_id          INT UNSIGNED NOT NULL,
  rating           TINYINT UNSIGNED NOT NULL,
  comment          TEXT,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_rev_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_rev_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT chk_rev_rating CHECK (rating BETWEEN 1 AND 5),
  KEY idx_rev_accommodation (accommodation_id)
) ENGINE=InnoDB;

-- keep accommodations.rating_avg / review_count in sync automatically
DELIMITER $$

CREATE TRIGGER trg_reviews_after_insert
AFTER INSERT ON reviews
FOR EACH ROW
BEGIN
  UPDATE accommodations a
  SET review_count = (SELECT COUNT(*) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_avg    = (SELECT ROUND(AVG(rating),1) FROM reviews WHERE accommodation_id = NEW.accommodation_id)
  WHERE a.id = NEW.accommodation_id;
END$$

CREATE TRIGGER trg_reviews_after_update
AFTER UPDATE ON reviews
FOR EACH ROW
BEGIN
  UPDATE accommodations a
  SET review_count = (SELECT COUNT(*) FROM reviews WHERE accommodation_id = NEW.accommodation_id),
      rating_avg    = (SELECT ROUND(AVG(rating),1) FROM reviews WHERE accommodation_id = NEW.accommodation_id)
  WHERE a.id = NEW.accommodation_id;
END$$

CREATE TRIGGER trg_reviews_after_delete
AFTER DELETE ON reviews
FOR EACH ROW
BEGIN
  UPDATE accommodations a
  SET review_count = (SELECT COUNT(*) FROM reviews WHERE accommodation_id = OLD.accommodation_id),
      rating_avg    = (SELECT IFNULL(ROUND(AVG(rating),1),0) FROM reviews WHERE accommodation_id = OLD.accommodation_id)
  WHERE a.id = OLD.accommodation_id;
END$$

DELIMITER ;

-- ------------------------------------------------------------
-- 4. Semantic search support (extension tables)
-- ------------------------------------------------------------
-- The FAISS vector index itself lives in the Python service's memory/disk,
-- not in MySQL. This table is only a durable backup / sync record so the
-- index can be rebuilt after a deploy or a data change.

CREATE TABLE accommodation_embeddings (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  accommodation_id INT UNSIGNED NOT NULL,
  model_name       VARCHAR(100) NOT NULL,          -- e.g. 'multilingual-e5-small'
  embedding_json   JSON NOT NULL,                  -- serialized float vector
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_emb_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  UNIQUE KEY uq_emb_accommodation (accommodation_id)
) ENGINE=InnoDB;

-- optional analytics: what people actually search for, and what the
-- rule-based parser extracted, useful for tuning the concept/synonym map
CREATE TABLE search_logs (
  id                     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id                INT UNSIGNED NULL,
  query_text             VARCHAR(500) NOT NULL,
  extracted_price_max    DECIMAL(10,2) NULL,
  extracted_district_id  INT UNSIGNED NULL,
  result_count           INT UNSIGNED NOT NULL DEFAULT 0,
  created_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_log_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_log_district
    FOREIGN KEY (extracted_district_id) REFERENCES districts(id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 5. Seed data — reference tables only (safe to run repeatedly)
-- ------------------------------------------------------------

INSERT INTO accommodation_types (code, name_th, icon_key) VALUES
  ('hotel',    'โรงแรม',   'building'),
  ('resort',   'รีสอร์ต',  'palm'),
  ('homestay', 'โฮมสเตย์', 'home')
ON DUPLICATE KEY UPDATE name_th = VALUES(name_th);

INSERT INTO amenities (code, label_th, icon_key) VALUES
  ('wifi',      'Wi-Fi ฟรี',              'wifi'),
  ('parking',   'ที่จอดรถ',               'parking'),
  ('breakfast', 'อาหารเช้า',              'breakfast'),
  ('pool',      'สระว่ายน้ำ',             'pool'),
  ('family',    'ห้องสำหรับครอบครัว',    'family'),
  ('pet',       'สัตว์เลี้ยงเข้าพักได้',  'pet')
ON DUPLICATE KEY UPDATE label_th = VALUES(label_th);

INSERT INTO districts (name, landmark_name, center_lat, center_lng) VALUES
  ('เมืองพิษณุโลก', 'วัดพระศรีรัตนมหาธาตุวรมหาวิหาร', 16.8211, 100.2659),
  ('พรหมพิราม',     'วัดพรหมพิราม',                    17.0500, 100.1333),
  ('ชาติตระการ',    'อุทยานแห่งชาติภูสอยดาว',          17.3167, 100.7833),
  ('บางกระทุ่ม',     'สวนผลไม้ริมน่าน',                 16.6167, 100.2667),
  ('วังทอง',         'อุทยานแห่งชาติทุ่งแสลงหลวง',     16.8333, 100.5333),
  ('นครไทย',         'อุทยานแห่งชาติภูหินร่องกล้า',     17.1167, 100.8667),
  ('วัดโบสถ์',       'น้ำตกวังก้านเหลือง',              17.0000, 100.2667),
  ('บางระกำ',        'ทุ่งบางระกำ',                     16.7500, 100.1333),
  ('เนินมะปราง',     'ถ้ำเจดีย์งาม',                    16.6500, 100.5833)
ON DUPLICATE KEY UPDATE landmark_name = VALUES(landmark_name);
