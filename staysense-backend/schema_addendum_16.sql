-- Run after schema_addendum_15.sql (or: python apply_addenda.py).
--
-- Homepage personalization (4 audience states: anonymous, searching,
-- logged-in-no-data, logged-in-with-data) needs three things that don't
-- exist anywhere yet:
--
--  1. accommodations.is_featured — admin-curated flag for "ที่พักน่าสนใจ
--     ในพิษณุโลก", shown while there isn't enough real usage data for a
--     genuine popularity ranking.
--  2. accommodation_events — a real usage-event log (view / favorite /
--     compare / contact_click / direction_click) so "ที่พักยอดนิยม" can be
--     computed from actual behavior instead of being invented.
--  3. user_preferences — what a member explicitly told the "บอกความ
--     ต้องการของคุณ" onboarding box, so personalized reasons can cite real
--     stored data instead of guessing.
--  4. users.allow_personalization — a member-controlled opt-out for using
--     their search history in recommendations (privacy requirement).

ALTER TABLE accommodations
  ADD COLUMN is_featured BOOLEAN NOT NULL DEFAULT FALSE AFTER status;

ALTER TABLE users
  ADD COLUMN allow_personalization BOOLEAN NOT NULL DEFAULT TRUE AFTER is_active;

CREATE TABLE IF NOT EXISTS accommodation_events (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  accommodation_id INT UNSIGNED NOT NULL,
  user_id          INT UNSIGNED NULL,
  event_type       ENUM('view', 'favorite', 'compare', 'contact_click', 'direction_click') NOT NULL,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_event_accommodation
    FOREIGN KEY (accommodation_id) REFERENCES accommodations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_event_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,

  KEY idx_event_acc_type_time (accommodation_id, event_type, created_at),
  KEY idx_event_user_time (user_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id               INT UNSIGNED PRIMARY KEY,
  type_codes            JSON NULL,
  district_names        JSON NULL,
  budget_min            DECIMAL(10,2) NULL,
  budget_max            DECIMAL(10,2) NULL,
  guest_count           INT UNSIGNED NULL,
  amenity_codes         JSON NULL,
  atmosphere_codes      JSON NULL,
  near_place_categories JSON NULL,
  updated_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_pref_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;
