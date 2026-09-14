-- Run after schema_addendum_9.sql (or: python apply_addenda.py).
--
-- Admin scope 4.3 (image management): captions and source/attribution notes
-- on both accommodation photos and room-type photos. Cover selection and
-- ordering already existed (is_cover / sort_order) — this just adds the
-- two text fields the admin UI needs to fill in.

ALTER TABLE accommodation_images
  ADD COLUMN caption     VARCHAR(255) NULL AFTER sort_order,
  ADD COLUMN source_note VARCHAR(255) NULL AFTER caption;

ALTER TABLE room_type_images
  ADD COLUMN caption     VARCHAR(255) NULL AFTER sort_order,
  ADD COLUMN source_note VARCHAR(255) NULL AFTER caption;
