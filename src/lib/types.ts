export type NodeStatus = "queued" | "proven" | "disproven" | "waiting" | "root_candidate" | "root_confirmed" | "stopped";
export type NodeType = "event" | "standing_condition";
export type Area = "equipment" | "people" | "environment_area" | "procedures_work_process" | "organization_management_system";

export type Fact = {
  id: string;
  statement: string;
  source: string;
  verified: boolean;
};

export type Thing = {
  id: string;
  name: string;
  category: string;
  provenance: "explicit" | "inferred";
  rationale?: string;
};

export type CausalNode = {
  id: string;
  statement: string;
  parentId?: string;
  depth: number;
  status: NodeStatus;
  type?: NodeType;
  area?: Area;
  factIds: string[];
  notes: string[];
};

export type Board = {
  focalPoint?: string;
  nodes: CausalNode[];
  queue: string[];
  version: number;
};

export type ProviderConfig = {
  id: string;
  name: string;
  kind: "ollama" | "openai_compatible";
  baseUrl: string;
  apiKeyEnvVar?: string;
  enabled: boolean;
};

export type ModelConfig = {
  providerId: string;
  model: string;
  temperature: number;
  maxDepth: number;
};

export type TraceEvent = {
  role: string;
  input: unknown;
  output: unknown;
  elapsedMs: number;
  valid: boolean;
  error?: string;
};

export type RunResult = {
  id: string;
  caseId: string;
  model: ModelConfig;
  board: Board;
  things: Thing[];
  traces: TraceEvent[];
  startedAt: string;
  finishedAt: string;
};
