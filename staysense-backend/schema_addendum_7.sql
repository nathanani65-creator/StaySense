-- Run after schema_addendum_6.sql (or: python apply_addenda.py).
--
-- Fills out room_types for the redesigned "ประเภทห้องพัก" cards:
--   * view_type          — วิวจากห้อง (garden / river / city / mountain / pool / none)
--   * room_amenities_json — สิ่งที่มีในห้องนี้ (aircon / wifi / tv / fridge / …)
--   * extra_bed_max       — เพิ่มเตียงเสริมได้สูงสุดกี่เตียง
--   * children/smoking/pets_allowed — กติกาของห้องประเภทนี้ (NULL = ไม่ระบุ)
-- Plus room_type_images: multiple photos per room type for the gallery modal.

ALTER TABLE room_types
  ADD COLUMN view_type          VARCHAR(20)  NULL AFTER bed_type,
  ADD COLUMN room_amenities_json JSON        NULL AFTER description,
  ADD COLUMN extra_bed_max       INT UNSIGNED NULL AFTER extra_bed_price,
  ADD COLUMN children_allowed    BOOLEAN      NULL AFTER units_available,
  ADD COLUMN smoking_allowed     BOOLEAN      NULL AFTER children_allowed,
  ADD COLUMN pets_allowed        BOOLEAN      NULL AFTER smoking_allowed;

CREATE TABLE room_type_images (
  id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  room_type_id INT UNSIGNED NOT NULL,
  image_url    VARCHAR(500) NOT NULL,
  sort_order   INT UNSIGNED NOT NULL DEFAULT 0,

  CONSTRAINT fk_rti_room_type
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
    ON UPDATE CASCADE ON DELETE CASCADE,

  KEY idx_rti_room_type (room_type_id)
) ENGINE=InnoDB;
