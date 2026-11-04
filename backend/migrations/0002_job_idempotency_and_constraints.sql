ALTER TABLE generation_jobs ADD COLUMN request_key VARCHAR(128);
UPDATE generation_jobs SET request_key = 'legacy-' || id::text WHERE request_key IS NULL;
ALTER TABLE generation_jobs ALTER COLUMN request_key SET NOT NULL;
ALTER TABLE generation_jobs ADD CONSTRAINT uq_generation_job_user_request UNIQUE (user_id, request_key);
ALTER TABLE generation_jobs ADD CONSTRAINT ck_generation_job_status
  CHECK (status IN ('queued', 'reserved', 'running', 'succeeded', 'failed', 'cancelled'));
ALTER TABLE credit_reservations ADD CONSTRAINT ck_credit_reservation_status
  CHECK (status IN ('reserved', 'settled', 'refunded'));
