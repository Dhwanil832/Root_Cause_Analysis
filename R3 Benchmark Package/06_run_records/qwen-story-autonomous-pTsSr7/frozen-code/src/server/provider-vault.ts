import { env } from 'cloudflare:workers';
import type { ModelDescriptor, ProviderConfig } from '@/src/domain/types';

interface ProviderRow {
  id: string;
  name: string;
  base_url: string;
  api_mode: ProviderConfig['apiMode'];
  model_ids_json: string;
  credential_ciphertext: string;
  credential_iv: string;
  key_hint: string;
  enabled: number;
  created_at: string;
  updated_at: string;
}

function database() {
  if (!env.DB) throw new Error('The D1 binding DB is unavailable.');
  return env.DB;
}

function bytesToBase64(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes));
}

function base64ToBytes(value: string) {
  return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
}

async function vaultKey() {
  const secret = process.env.PROVIDER_VAULT_KEY;
  if (!secret || secret.length < 32) throw new Error('PROVIDER_VAULT_KEY must be configured before API credentials can be stored.');
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(secret));
  return crypto.subtle.importKey('raw', digest, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
}

async function encryptCredential(value: string) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, await vaultKey(), new TextEncoder().encode(value));
  return { ciphertext: bytesToBase64(new Uint8Array(ciphertext)), iv: bytesToBase64(iv) };
}

async function decryptCredential(ciphertext: string, iv: string) {
  const plaintext = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: base64ToBytes(iv) },
    await vaultKey(),
    base64ToBytes(ciphertext),
  );
  return new TextDecoder().decode(plaintext);
}

function publicConfig(row: ProviderRow): ProviderConfig {
  return {
    id: row.id,
    name: row.name,
    baseUrl: row.base_url,
    apiMode: row.api_mode,
    modelIds: JSON.parse(row.model_ids_json) as string[],
    keyHint: row.key_hint,
    enabled: Boolean(row.enabled),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function normalizeUrl(value: string) {
  const url = new URL(value.trim());
  if (!['https:', 'http:'].includes(url.protocol)) throw new Error('Provider URL must use HTTP or HTTPS.');
  if (url.protocol === 'http:' && !['localhost', '127.0.0.1'].includes(url.hostname)) {
    throw new Error('Remote provider URLs must use HTTPS.');
  }
  return url.toString().replace(/\/$/, '');
}

function normalizeModels(values: string[]) {
  const models = [...new Set(values.map((value) => value.trim()).filter(Boolean))];
  if (!models.length) throw new Error('Add at least one provider model ID.');
  if (models.length > 40) throw new Error('A provider may list at most 40 models.');
  return models;
}

export async function listProviderConfigs() {
  const rows = await database().prepare('SELECT * FROM provider_configs ORDER BY name').all<ProviderRow>();
  return rows.results.map(publicConfig);
}

export async function saveProviderConfig(input: {
  id?: string;
  name: string;
  baseUrl: string;
  apiMode: ProviderConfig['apiMode'];
  modelIds: string[];
  apiKey?: string;
  enabled?: boolean;
}) {
  const name = input.name.trim();
  if (!name) throw new Error('Provider name is required.');
  const baseUrl = normalizeUrl(input.baseUrl);
  const modelIds = normalizeModels(input.modelIds);
  const now = new Date().toISOString();

  if (input.id) {
    const existing = await database().prepare('SELECT * FROM provider_configs WHERE id = ?').bind(input.id).first<ProviderRow>();
    if (!existing) throw new Error('Provider was not found.');
    let ciphertext = existing.credential_ciphertext;
    let iv = existing.credential_iv;
    let keyHint = existing.key_hint;
    if (input.apiKey?.trim()) {
      const encrypted = await encryptCredential(input.apiKey.trim());
      ciphertext = encrypted.ciphertext;
      iv = encrypted.iv;
      keyHint = `••••${input.apiKey.trim().slice(-4)}`;
    }
    await database().prepare([
      'UPDATE provider_configs SET name = ?, base_url = ?, api_mode = ?, model_ids_json = ?,',
      'credential_ciphertext = ?, credential_iv = ?, key_hint = ?, enabled = ?, updated_at = ? WHERE id = ?',
    ].join(' ')).bind(
      name, baseUrl, input.apiMode, JSON.stringify(modelIds), ciphertext, iv, keyHint,
      (input.enabled ?? Boolean(existing.enabled)) ? 1 : 0, now, input.id,
    ).run();
    const updated = await database().prepare('SELECT * FROM provider_configs WHERE id = ?').bind(input.id).first<ProviderRow>();
    return publicConfig(updated!);
  }

  if (!input.apiKey?.trim()) throw new Error('API key is required for a new provider.');
  const encrypted = await encryptCredential(input.apiKey.trim());
  const id = crypto.randomUUID();
  await database().prepare([
    'INSERT INTO provider_configs (id, name, base_url, api_mode, model_ids_json, credential_ciphertext,',
    'credential_iv, key_hint, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  ].join(' ')).bind(
    id, name, baseUrl, input.apiMode, JSON.stringify(modelIds), encrypted.ciphertext,
    encrypted.iv, `••••${input.apiKey.trim().slice(-4)}`, input.enabled === false ? 0 : 1, now, now,
  ).run();
  const created = await database().prepare('SELECT * FROM provider_configs WHERE id = ?').bind(id).first<ProviderRow>();
  return publicConfig(created!);
}

export async function deleteProviderConfig(id: string) {
  const usage = await database().prepare('SELECT COUNT(*) AS count FROM model_tracks WHERE model_id LIKE ?').bind(`hosted:${id}:%`).first<{ count: number }>();
  if ((usage?.count || 0) > 0) throw new Error('This provider is used by preserved model tracks. Disable it instead of deleting it.');
  await database().prepare('DELETE FROM provider_configs WHERE id = ?').bind(id).run();
}

export async function providerModels(): Promise<ModelDescriptor[]> {
  const configs = await listProviderConfigs();
  return configs.flatMap((config) => config.modelIds.map((modelId) => ({
    id: `hosted:${config.id}:${encodeURIComponent(modelId)}`,
    name: modelId,
    provider: 'openai-compatible' as const,
    detail: `${config.name} · hosted`,
    available: config.enabled,
    providerConfigId: config.id,
    capabilities: ['vision', ...(config.apiMode === 'responses' ? ['files'] : [])],
  })));
}

export async function resolveHostedModel(id: string): Promise<ModelDescriptor | null> {
  const match = id.match(/^hosted:([^:]+):(.+)$/);
  if (!match) return null;
  const row = await database().prepare('SELECT * FROM provider_configs WHERE id = ?').bind(match[1]).first<ProviderRow>();
  if (!row) return null;
  return {
    id,
    name: decodeURIComponent(match[2]),
    provider: 'openai-compatible',
    detail: `${row.name} · hosted`,
    available: Boolean(row.enabled),
    providerConfigId: row.id,
    baseUrl: row.base_url,
    apiKey: await decryptCredential(row.credential_ciphertext, row.credential_iv),
    apiMode: row.api_mode,
    capabilities: ['vision', ...(row.api_mode === 'responses' ? ['files'] : [])],
  };
}

export async function testProviderConfig(id: string) {
  const row = await database().prepare('SELECT * FROM provider_configs WHERE id = ?').bind(id).first<ProviderRow>();
  if (!row) throw new Error('Provider was not found.');
  const response = await fetch(`${row.base_url}/models`, {
    headers: { authorization: `Bearer ${await decryptCredential(row.credential_ciphertext, row.credential_iv)}` },
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) throw new Error(`Provider returned ${response.status} while listing models.`);
  return { ok: true, status: response.status };
}
