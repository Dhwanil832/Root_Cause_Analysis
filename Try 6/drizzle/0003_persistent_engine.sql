CREATE TABLE engine_runs (
  id TEXT PRIMARY KEY NOT NULL, track_id TEXT NOT NULL, number INTEGER NOT NULL,
  parent_number INTEGER NOT NULL, status TEXT NOT NULL, trigger TEXT NOT NULL,
  input_json TEXT NOT NULL, state_json TEXT, snapshot_json TEXT NOT NULL,
  lease TEXT, lease_until INTEGER NOT NULL DEFAULT 0, generation INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(track_id, number)
);
--> statement-breakpoint
CREATE INDEX engine_runs_ready ON engine_runs(status, lease_until, created_at);
--> statement-breakpoint
CREATE TABLE engine_task_cache (
  track_id TEXT NOT NULL, cache_key TEXT NOT NULL, kind TEXT NOT NULL,
  output_json TEXT NOT NULL, evidence_json TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(track_id, cache_key)
);
--> statement-breakpoint
CREATE TABLE engine_task_events (
  id TEXT PRIMARY KEY NOT NULL, run_id TEXT NOT NULL, task_id TEXT NOT NULL,
  kind TEXT NOT NULL, status TEXT NOT NULL, attempt INTEGER NOT NULL,
  payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
--> statement-breakpoint
CREATE INDEX engine_task_events_run ON engine_task_events(run_id, created_at);
--> statement-breakpoint
CREATE TABLE extraction_cache (
  cache_key TEXT PRIMARY KEY NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL
);
