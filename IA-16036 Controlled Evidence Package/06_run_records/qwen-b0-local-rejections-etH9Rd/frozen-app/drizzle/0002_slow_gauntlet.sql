-- stage_checkpoints was already created by 0002_stage_checkpoints.sql.
CREATE TABLE `story_rounds` (
	`id` text PRIMARY KEY NOT NULL,
	`scenario_id` text NOT NULL,
	`base_version` integer NOT NULL,
	`status` text NOT NULL,
	`questions_json` text NOT NULL,
	`output_json` text NOT NULL,
	`error` text NOT NULL,
	`result_version` integer,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `story_round_base_idx` ON `story_rounds` (`scenario_id`,`base_version`);--> statement-breakpoint
CREATE TABLE `story_scenarios` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`title` text NOT NULL,
	`model_id` text NOT NULL,
	`scenario_json` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `story_scenarios_track_id_unique` ON `story_scenarios` (`track_id`);
