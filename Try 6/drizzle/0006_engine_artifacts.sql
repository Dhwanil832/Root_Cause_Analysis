CREATE TABLE `engine_artifact_chunks` (
	`artifact_id` text NOT NULL,
	`ordinal` integer NOT NULL,
	`content` text NOT NULL,
	PRIMARY KEY(`artifact_id`, `ordinal`)
);
--> statement-breakpoint
CREATE TABLE `engine_calls` (
	`id` text PRIMARY KEY NOT NULL,
	`run_id` text NOT NULL,
	`task_id` text NOT NULL,
	`attempt` integer NOT NULL,
	`request_json` text,
	`result_json` text,
	`status` text DEFAULT 'started' NOT NULL,
	`error` text DEFAULT '' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `engine_calls_run` ON `engine_calls` (`run_id`,`task_id`);--> statement-breakpoint
ALTER TABLE `engine_runs` ADD `pause_reason` text DEFAULT '' NOT NULL;