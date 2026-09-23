-- Widen image URL columns: Facebook's CDN (scontent.*.fna.fbcdn.net) puts
-- long signed query tokens on photo URLs that regularly exceed 500 chars
-- (seen up to ~590 chars in the Sep 2026 data import), so VARCHAR(500) was
-- silently dropping real photos rather than storing a truncated/invalid URL.
ALTER TABLE accommodation_images MODIFY COLUMN image_url VARCHAR(1024) NOT NULL;
ALTER TABLE accommodation_images MODIFY COLUMN thumbnail_url VARCHAR(1024) NULL;
ALTER TABLE accommodation_images MODIFY COLUMN source_url VARCHAR(1024) NULL;

ALTER TABLE room_type_images MODIFY COLUMN image_url VARCHAR(1024) NOT NULL;
ALTER TABLE room_type_images MODIFY COLUMN thumbnail_url VARCHAR(1024) NULL;
ALTER TABLE room_type_images MODIFY COLUMN source_url VARCHAR(1024) NULL;
