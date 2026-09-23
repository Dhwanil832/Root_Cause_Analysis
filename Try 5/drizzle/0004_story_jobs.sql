CREATE TABLE story_jobs (
 id TEXT PRIMARY KEY NOT NULL, round_id TEXT NOT NULL, question_id TEXT NOT NULL,
 question_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
 output_json TEXT NOT NULL DEFAULT '{}', error TEXT NOT NULL DEFAULT '',
 lease TEXT, lease_until INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(round_id, question_id)
);
--> statement-breakpoint
CREATE INDEX story_jobs_ready ON story_jobs(status, lease_until, created_at);
