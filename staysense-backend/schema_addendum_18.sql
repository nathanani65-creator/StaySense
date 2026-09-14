-- Run after schema_addendum_17.sql (or: python apply_addenda.py).
--
-- Full image-management system: rich metadata + status + real-file upload
-- support for both accommodation_images (whole-property gallery) and
-- room_type_images (per-room-type gallery, kept strictly separate — see
-- app/routers/images.py). room_type_images never had its own is_cover
-- column before; every room type needs one independent of the others.

ALTER TABLE accommodation_images ADD COLUMN image_category VARCHAR(50) NULL AFTER image_url;
ALTER TABLE accommodation_images ADD COLUMN thumbnail_url VARCHAR(500) NULL AFTER image_category;
ALTER TABLE accommodation_images ADD COLUMN alt_text VARCHAR(255) NULL AFTER caption;
ALTER TABLE accommodation_images ADD COLUMN source_name VARCHAR(150) NULL AFTER alt_text;
ALTER TABLE accommodation_images ADD COLUMN source_url VARCHAR(500) NULL AFTER source_name;
ALTER TABLE accommodation_images ADD COLUMN status ENUM('published','hidden','pending') NOT NULL DEFAULT 'published' AFTER is_cover;
ALTER TABLE accommodation_images ADD COLUMN uploaded_by INT UNSIGNED NULL AFTER status;
ALTER TABLE accommodation_images ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER uploaded_by;
ALTER TABLE accommodation_images ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;
ALTER TABLE accommodation_images ADD CONSTRAINT fk_accimg_uploader FOREIGN KEY (uploaded_by) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL;
ALTER TABLE accommodation_images ADD KEY idx_accimg_status (accommodation_id, status);

ALTER TABLE room_type_images ADD COLUMN is_cover BOOLEAN NOT NULL DEFAULT FALSE AFTER sort_order;
ALTER TABLE room_type_images ADD COLUMN image_category VARCHAR(50) NULL AFTER image_url;
ALTER TABLE room_type_images ADD COLUMN thumbnail_url VARCHAR(500) NULL AFTER image_category;
ALTER TABLE room_type_images ADD COLUMN alt_text VARCHAR(255) NULL AFTER caption;
ALTER TABLE room_type_images ADD COLUMN source_name VARCHAR(150) NULL AFTER alt_text;
ALTER TABLE room_type_images ADD COLUMN source_url VARCHAR(500) NULL AFTER source_name;
ALTER TABLE room_type_images ADD COLUMN status ENUM('published','hidden','pending') NOT NULL DEFAULT 'published' AFTER is_cover;
ALTER TABLE room_type_images ADD COLUMN uploaded_by INT UNSIGNED NULL AFTER status;
ALTER TABLE room_type_images ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER uploaded_by;
ALTER TABLE room_type_images ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;
ALTER TABLE room_type_images ADD CONSTRAINT fk_rtimg_uploader FOREIGN KEY (uploaded_by) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL;
ALTER TABLE room_type_images ADD KEY idx_rtimg_status (room_type_id, status);

CREATE TABLE IF NOT EXISTS image_audit_log (
  id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  admin_user_id   INT UNSIGNED NULL,
  action          VARCHAR(30) NOT NULL,             -- create|update|cover|status|reorder|delete
  image_group     VARCHAR(20) NOT NULL,             -- accommodation|room_type
  accommodation_id INT UNSIGNED NULL,
  room_type_id    INT UNSIGNED NULL,
  image_id        INT UNSIGNED NOT NULL,
  old_value       JSON NULL,
  new_value       JSON NULL,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_imgaudit_admin
    FOREIGN KEY (admin_user_id) REFERENCES users(id)
    ON UPDATE CASCADE ON DELETE SET NULL,

  KEY idx_imgaudit_acc (accommodation_id, created_at),
  KEY idx_imgaudit_room (room_type_id, created_at)
) ENGINE=InnoDB;
