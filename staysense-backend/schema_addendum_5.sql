-- Run this after schema_addendum_4.sql (or: python apply_addenda.py).
--
-- Adds three groups of fields to `accommodations`:
--   1. Pricing conditions — deposit amount / percent, advance-booking rule,
--      free-text price conditions (high season, long weekends, extra guests…)
--   2. Contact channels — LINE / Facebook / Instagram / website
--      (phone already exists)
--   3. google_maps_url — the shareable Google Maps place link, used in
--      preference to the raw lat/lng which often points at the wrong spot
--
-- Everything is nullable / defaulted, so existing rows stay valid.

ALTER TABLE accommodations
  ADD COLUMN deposit_amount           DECIMAL(10,2) NULL          AFTER deposit_note,
  ADD COLUMN deposit_percent          TINYINT UNSIGNED NULL       AFTER deposit_amount,
  ADD COLUMN advance_booking_required BOOLEAN NOT NULL DEFAULT FALSE AFTER deposit_percent,
  ADD COLUMN advance_booking_days     INT UNSIGNED NULL           AFTER advance_booking_required,
  ADD COLUMN price_conditions         TEXT NULL                   AFTER advance_booking_days,
  ADD COLUMN contact_line             VARCHAR(120) NULL           AFTER phone,
  ADD COLUMN contact_facebook         VARCHAR(255) NULL           AFTER contact_line,
  ADD COLUMN contact_instagram        VARCHAR(120) NULL           AFTER contact_facebook,
  ADD COLUMN website_url              VARCHAR(255) NULL           AFTER contact_instagram,
  ADD COLUMN google_maps_url          VARCHAR(500) NULL           AFTER website_url;
