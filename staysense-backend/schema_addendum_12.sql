-- Run after schema_addendum_11.sql (or: python apply_addenda.py).
--
-- Admin scope 4.5 (place management): address and a source/reference note
-- for each curated place, so admins editing places.* have the same
-- data-quality fields already used on accommodations.

ALTER TABLE places
  ADD COLUMN address     VARCHAR(300) NULL AFTER longitude,
  ADD COLUMN source_note VARCHAR(255) NULL AFTER is_popular;
