-- Run after schema_addendum_18.sql (or: python apply_addenda.py).
--
-- Semantic search upgrade: typo/informal-term dictionary (search_terms),
-- richer search_logs (what the query normalized to + the parsed intent, for
-- admin visibility into what the search system understood), and a per-user
-- opt-out for search-history logging (mirrors users.allow_personalization).

CREATE TABLE IF NOT EXISTS search_terms (
  search_term_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  input_term     VARCHAR(100) NOT NULL,
  canonical_term VARCHAR(150) NOT NULL,
  term_type      ENUM('accommodation_type','poi_category','poi_name','facility','district','general') NOT NULL,
  reference_id   INT UNSIGNED NULL,
  confidence     DECIMAL(3,2) NOT NULL DEFAULT 1.00,
  status         ENUM('active','inactive') NOT NULL DEFAULT 'active',
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uq_searchterm_input (input_term),
  KEY idx_searchterm_status (status)
) ENGINE=InnoDB;

ALTER TABLE search_logs ADD COLUMN normalized_query VARCHAR(500) NULL AFTER query_text;
ALTER TABLE search_logs ADD COLUMN detected_intent_json JSON NULL AFTER normalized_query;
ALTER TABLE search_logs ADD COLUMN confidence DECIMAL(3,2) NULL AFTER detected_intent_json;

ALTER TABLE users ADD COLUMN save_search_history BOOLEAN NOT NULL DEFAULT TRUE AFTER allow_personalization;

-- accommodation-type / general typos and informal terms (spec §10-11 examples)
INSERT INTO search_terms (input_term, canonical_term, term_type) VALUES
  ('โรงแรง',   'โรงแรม',   'accommodation_type'),
  ('โรงเเรม',  'โรงแรม',   'accommodation_type'),
  ('รร.',      'โรงแรม',   'accommodation_type'),
  ('รีสอร์ท',  'รีสอร์ต',  'accommodation_type'),
  ('รีสอด',    'รีสอร์ต',  'accommodation_type'),
  ('โฮมเสต',   'โฮมสเตย์', 'accommodation_type'),
  ('โฮมสเตย',  'โฮมสเตย์', 'accommodation_type'),
  ('วัส',      'วัด',      'poi_category'),
  ('วัค',      'วัด',      'poi_category'),
  ('ใกล่',     'ใกล้',     'general'),
  ('สะว่ายน้ำ','สระว่ายน้ำ','facility'),
  ('สระน้ำ',   'สระว่ายน้ำ','facility'),
  ('ที่จอดลด', 'ที่จอดรถ', 'facility'),
  ('พิดโลก',   'พิษณุโลก', 'general'),
  ('พิโลก',    'พิษณุโลก', 'general'),
  ('ร้านเหล้า','สถานบันเทิง','poi_category'),
  ('ผับ',      'สถานบันเทิง','poi_category'),
  ('บาร์',     'สถานบันเทิง','poi_category'),
  ('ร้านนั่งชิล','สถานบันเทิง','poi_category'),
  ('ห้าง',     'ห้างสรรพสินค้า','poi_category'),
  ('ศูนย์การค้า','ห้างสรรพสินค้า','poi_category'),
  ('รพ.',      'โรงพยาบาล','poi_category'),
  ('โรงบาล',   'โรงพยาบาล','poi_category')
ON DUPLICATE KEY UPDATE canonical_term = VALUES(canonical_term), term_type = VALUES(term_type);

-- ม.นเรศวร / มอนอ → link to a real places row when one exists (name match),
-- otherwise still normalize the text without inventing a POI link.
INSERT INTO search_terms (input_term, canonical_term, term_type, reference_id)
SELECT t.input_term, 'มหาวิทยาลัยนเรศวร', 'poi_name', p.id
FROM (SELECT 'มอนอ' AS input_term UNION ALL SELECT 'ม.นเรศวร') t
LEFT JOIN places p ON LOCATE('นเรศวร', p.name) > 0
ON DUPLICATE KEY UPDATE canonical_term = VALUES(canonical_term), reference_id = VALUES(reference_id);
