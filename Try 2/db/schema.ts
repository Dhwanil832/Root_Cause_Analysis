import { integer, sqliteTable, text } from 'drizzle-orm/sqlite-core';

export const incidents = sqliteTable('incidents', {
  id: text('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description').notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
});

export const modelTracks = sqliteTable('model_tracks', {
  id: text('id').primaryKey(),
  incidentId: text('incident_id').notNull(),
  modelId: text('model_id').notNull(),
  modelName: text('model_name').notNull(),
  provider: text('provider').notNull(),
  createdAt: text('created_at').notNull(),
});

export const versions = sqliteTable('versions', {
  id: text('id').primaryKey(),
  trackId: text('track_id').notNull(),
  number: integer('number').notNull(),
  trigger: text('trigger').notNull(),
  analysisJson: text('analysis_json').notNull(),
  createdAt: text('created_at').notNull(),
});

export const documents = sqliteTable('documents', {
  id: text('id').primaryKey(),
  trackId: text('track_id').notNull(),
  questionId: text('question_id').notNull(),
  fileKey: text('file_key').notNull(),
  fileName: text('file_name').notNull(),
  contentType: text('content_type').notNull(),
  size: integer('size').notNull(),
  createdAt: text('created_at').notNull(),
});
