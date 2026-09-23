CREATE TABLE `stage_checkpoints` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`run_id` text NOT NULL,
	`target_version` integer NOT NULL,
	`sequence` integer NOT NULL,
	`stage` text NOT NULL,
	`status` text NOT NULL,
	`payload_json` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `stage_checkpoints_track_idx` ON `stage_checkpoints` (`track_id`);
--> statement-breakpoint
CREATE INDEX `stage_checkpoints_run_idx` ON `stage_checkpoints` (`run_id`);
--> statement-breakpoint
CREATE UNIQUE INDEX `stage_checkpoints_run_sequence_idx` ON `stage_checkpoints` (`run_id`,`sequence`);
