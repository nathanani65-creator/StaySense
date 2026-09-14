-- Run after schema_addendum_10.sql (or: python apply_addenda.py).
--
-- Admin scope 4.4 (amenity management): a real category column on amenities,
-- replacing the frontend-only AMENITY_CATEGORIES grouping so admins can
-- assign/reassign categories through the admin UI instead of code edits.

ALTER TABLE amenities
  ADD COLUMN category VARCHAR(30) NULL AFTER icon_key;

UPDATE amenities SET category = 'room'         WHERE code IN ('aircon', 'tv', 'fridge', 'water_heater');
UPDATE amenities SET category = 'property'     WHERE code IN ('wifi', 'pool', 'restaurant', 'gym', 'elevator');
UPDATE amenities SET category = 'service'      WHERE code IN ('breakfast', 'laundry', 'reception24');
UPDATE amenities SET category = 'parking'      WHERE code IN ('parking');
UPDATE amenities SET category = 'accessibility' WHERE code IN ('family', 'pet', 'wheelchair', 'elderly');
UPDATE amenities SET category = 'other' WHERE category IS NULL;
