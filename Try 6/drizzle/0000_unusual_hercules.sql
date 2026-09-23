CREATE TABLE `documents` (
	`id` text PRIMARY KEY NOT NULL,
	`scope` text NOT NULL,
	`title` text NOT NULL,
	`plant` text NOT NULL,
	`incident_id` text,
	`track_id` text,
	`question_id` text,
	`introduced_version` integer,
	`file_key` text NOT NULL,
	`file_name` text NOT NULL,
	`content_type` text NOT NULL,
	`size` integer NOT NULL,
	`sha256` text NOT NULL,
	`revision` text NOT NULL,
	`extraction_status` text NOT NULL,
	`extraction_notes` text NOT NULL,
	`extracted_text` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `documents_scope_idx` ON `documents` (`scope`);--> statement-breakpoint
CREATE INDEX `documents_incident_idx` ON `documents` (`incident_id`);--> statement-breakpoint
CREATE INDEX `documents_track_idx` ON `documents` (`track_id`);--> statement-breakpoint
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
CREATE INDEX `model_tracks_incident_idx` ON `model_tracks` (`incident_id`);--> statement-breakpoint
CREATE TABLE `track_documents` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`document_id` text NOT NULL,
	`source_scope` text NOT NULL,
	`introduced_version` integer NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `track_documents_track_idx` ON `track_documents` (`track_id`);--> statement-breakpoint
CREATE UNIQUE INDEX `track_documents_unique_idx` ON `track_documents` (`track_id`,`document_id`);--> statement-breakpoint
CREATE TABLE `versions` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`number` integer NOT NULL,
	`trigger` text NOT NULL,
	`analysis_json` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `versions_track_idx` ON `versions` (`track_id`);--> statement-breakpoint
CREATE UNIQUE INDEX `versions_track_number_idx` ON `versions` (`track_id`,`number`);