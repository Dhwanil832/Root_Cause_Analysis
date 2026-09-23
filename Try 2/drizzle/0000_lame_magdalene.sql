CREATE TABLE `documents` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`question_id` text NOT NULL,
	`file_key` text NOT NULL,
	`file_name` text NOT NULL,
	`content_type` text NOT NULL,
	`size` integer NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `incidents` (
	`id` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`description` text NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `model_tracks` (
	`id` text PRIMARY KEY NOT NULL,
	`incident_id` text NOT NULL,
	`model_id` text NOT NULL,
	`model_name` text NOT NULL,
	`provider` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `versions` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`number` integer NOT NULL,
	`trigger` text NOT NULL,
	`analysis_json` text NOT NULL,
	`created_at` text NOT NULL
);
