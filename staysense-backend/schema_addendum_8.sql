-- Run after schema_addendum_7.sql (or: python apply_addenda.py).
--
-- Narrows the accommodation catalogue to 3 categories — โรงแรม / รีสอร์ต /
-- โฮมสเตย์. Removes 'hostel' and 'guesthouse'. Safe only while no
-- accommodation row references them (fk_acc_type is ON DELETE RESTRICT);
-- reassign those first if any exist.

DELETE FROM accommodation_types WHERE code IN ('hostel', 'guesthouse');
