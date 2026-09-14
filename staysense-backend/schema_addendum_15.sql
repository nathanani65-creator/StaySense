-- Run after schema_addendum_14.sql (or: python apply_addenda.py).
--
-- room_types.description was VARCHAR(255), sized for the short admin-typed
-- blurbs used so far. Real collected room descriptions (plus an appended
-- "เงื่อนไขเพิ่มเติม" note) regularly exceed that — widen to TEXT.

ALTER TABLE room_types
  MODIFY COLUMN description TEXT NULL;
