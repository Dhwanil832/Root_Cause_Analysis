CREATE TABLE IF NOT EXISTS evidence_releases (
  track_id TEXT NOT NULL, release_id TEXT NOT NULL, parent_number INTEGER NOT NULL,
  payload_hash TEXT NOT NULL, run_id TEXT NOT NULL, number INTEGER NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(track_id,release_id), UNIQUE(track_id,number)
);
