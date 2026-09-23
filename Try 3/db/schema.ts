import { index, integer, sqliteTable, text, uniqueIndex } from 'drizzle-orm/sqlite-core';

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
}, (table) => [index('model_tracks_incident_idx').on(table.incidentId)]);

export const versions = sqliteTable('versions', {
  id: text('id').primaryKey(),
  trackId: text('track_id').notNull(),
  number: integer('number').notNull(),
  trigger: text('trigger').notNull(),
  analysisJson: text('analysis_json').notNull(),
  createdAt: text('created_at').notNull(),
}, (table) => [
  index('versions_track_idx').on(table.trackId),
  uniqueIndex('versions_track_number_idx').on(table.trackId, table.number),
]);

export const documents = sqliteTable('documents', {
  id: text('id').primaryKey(),
  scope: text('scope').notNull(),
  title: text('title').notNull(),
  plant: text('plant').notNull(),
  incidentId: text('incident_id'),
  trackId: text('track_id'),
  questionId: text('question_id'),
  introducedVersion: integer('introduced_version'),
  fileKey: text('file_key').notNull(),
  fileName: text('file_name').notNull(),
  contentType: text('content_type').notNull(),
  size: integer('size').notNull(),
  sha256: text('sha256').notNull(),
  revision: text('revision').notNull(),
  extractionStatus: text('extraction_status').notNull(),
  extractionNotes: text('extraction_notes').notNull(),
  extractedText: text('extracted_text').notNull(),
  createdAt: text('created_at').notNull(),
}, (table) => [
  index('documents_scope_idx').on(table.scope),
  index('documents_incident_idx').on(table.incidentId),
  index('documents_track_idx').on(table.trackId),
]);

export const trackDocuments = sqliteTable('track_documents', {
  id: text('id').primaryKey(),
  trackId: text('track_id').notNull(),
  documentId: text('document_id').notNull(),
  sourceScope: text('source_scope').notNull(),
  introducedVersion: integer('introduced_version').notNull(),
  createdAt: text('created_at').notNull(),
}, (table) => [
  index('track_documents_track_idx').on(table.trackId),
  uniqueIndex('track_documents_unique_idx').on(table.trackId, table.documentId),
]);

export const providerConfigs = sqliteTable('provider_configs', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  baseUrl: text('base_url').notNull(),
  apiMode: text('api_mode').notNull(),
  modelIdsJson: text('model_ids_json').notNull(),
  credentialCiphertext: text('credential_ciphertext').notNull(),
  credentialIv: text('credential_iv').notNull(),
  keyHint: text('key_hint').notNull(),
  enabled: integer('enabled', { mode: 'boolean' }).notNull(),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
});
