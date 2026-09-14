-- Run after schema_addendum_12.sql (or: python apply_addenda.py).
--
-- Admin scope 4.6 (members & stats): a real suspend/activate flag on users,
-- and start actually writing to search_logs (schema.sql created the table
-- but nothing ever inserted into it) so "popular/no-result search terms"
-- on the admin stats page reflects real usage instead of being faked.

ALTER TABLE users
  ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER role;
