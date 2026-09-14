-- Run after schema_addendum_8.sql (or: python apply_addenda.py).
--
-- Admin scope 4.1 (accommodation data management):
--   * status becomes an editorial workflow — draft / pending_review /
--     published / closed — instead of active/inactive, so admins can take
--     a listing down without deleting it. Existing rows: 'active' -> 'published',
--     'inactive' -> 'closed'.
--   * last_verified_at / source_note — when an admin last confirmed the data
--     is accurate, and where it came from.
--   * room_types.is_visible — hide one room type from the public site
--     without deleting it (e.g. seasonal room, temporarily unavailable).
--
-- MySQL can't ALTER an ENUM column to a value set that doesn't cover the
-- existing data in one step, so this migrates through a temp column.

ALTER TABLE accommodations
  ADD COLUMN status_new ENUM('draft','pending_review','published','closed') NOT NULL DEFAULT 'draft';

UPDATE accommodations
SET status_new = CASE status
  WHEN 'active' THEN 'published'
  WHEN 'inactive' THEN 'closed'
  ELSE 'draft'
END;

ALTER TABLE accommodations DROP KEY idx_acc_status;
ALTER TABLE accommodations DROP COLUMN status;
ALTER TABLE accommodations CHANGE COLUMN status_new status ENUM('draft','pending_review','published','closed') NOT NULL DEFAULT 'draft';
ALTER TABLE accommodations ADD KEY idx_acc_status (status);

ALTER TABLE accommodations
  ADD COLUMN last_verified_at DATE NULL AFTER updated_at,
  ADD COLUMN source_note VARCHAR(500) NULL AFTER last_verified_at;

ALTER TABLE room_types
  ADD COLUMN is_visible BOOLEAN NOT NULL DEFAULT TRUE AFTER sort_order;
