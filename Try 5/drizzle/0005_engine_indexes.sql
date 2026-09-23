CREATE UNIQUE INDEX IF NOT EXISTS engine_runs_track_number ON engine_runs(track_id, number);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS engine_task_cache_identity ON engine_task_cache(track_id, cache_key);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS story_jobs_question ON story_jobs(round_id, question_id);
