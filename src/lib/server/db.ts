import "server-only";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { indianaHarborIncident, seedFacts, seedThings } from "../seed";
import type { Fact, ProviderConfig, RunResult, Thing } from "../types";

const dataDirectory = join(process.cwd(), "data");
mkdirSync(dataDirectory, { recursive: true });
const db = new DatabaseSync(join(dataDirectory, "rca-harness.sqlite"));

db.exec(`
  CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, name TEXT NOT NULL, incident TEXT NOT NULL, facts TEXT NOT NULL, things TEXT NOT NULL, updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS providers (id TEXT PRIMARY KEY, config TEXT NOT NULL, updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL);
`);

function json<T>(value: string): T { return JSON.parse(value) as T; }

export function initialize() {
  const row = db.prepare("SELECT id FROM cases WHERE id = ?").get("indiana-harbor-r3") as { id?: string } | undefined;
  if (!row?.id) {
    db.prepare("INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?)").run(
      "indiana-harbor-r3", "Indiana Harbor R3 Exit Carrier Beam", indianaHarborIncident,
      JSON.stringify(seedFacts), JSON.stringify(seedThings), new Date().toISOString(),
    );
  }
  const provider = db.prepare("SELECT id FROM providers WHERE id = ?").get("ollama-local") as { id?: string } | undefined;
  if (!provider?.id) saveProvider({ id: "ollama-local", name: "Local Ollama", kind: "ollama", baseUrl: "http://localhost:11434/v1", enabled: true });
}

export function getCase(id = "indiana-harbor-r3") {
  initialize();
  const row = db.prepare("SELECT * FROM cases WHERE id = ?").get(id) as Record<string, string> | undefined;
  if (!row) throw new Error("Case not found");
  return { id: row.id, name: row.name, incident: row.incident, facts: json<Fact[]>(row.facts), things: json<Thing[]>(row.things), updatedAt: row.updated_at };
}

export function listProviders(): ProviderConfig[] {
  initialize();
  return (db.prepare("SELECT config FROM providers ORDER BY updated_at DESC").all() as { config: string }[]).map((row) => json<ProviderConfig>(row.config));
}

export function saveProvider(provider: ProviderConfig) {
  db.prepare("INSERT OR REPLACE INTO providers (id, config, updated_at) VALUES (?, ?, ?)").run(provider.id, JSON.stringify(provider), new Date().toISOString());
}

export function saveRun(run: RunResult) {
  db.prepare("INSERT INTO runs VALUES (?, ?, ?, ?)").run(run.id, run.caseId, JSON.stringify(run), run.startedAt);
}

export function listRuns(): RunResult[] {
  initialize();
  return (db.prepare("SELECT result FROM runs ORDER BY created_at DESC LIMIT 20").all() as { result: string }[]).map((row) => json<RunResult>(row.result));
}
