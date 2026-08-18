import "server-only";
import { randomUUID } from "node:crypto";
import { complete } from "./providers";
import type { Board, CausalNode, Fact, ModelConfig, ProviderConfig, RunResult, Thing, TraceEvent } from "../types";

type CaseInput = { id: string; incident: string; facts: Fact[]; things: Thing[] };

function context(input: CaseInput, board?: Board) {
  return JSON.stringify({ incident: input.incident, facts: input.facts, things: input.things, board }, null, 2);
}

export async function runHarness(input: CaseInput, provider: ProviderConfig, model: ModelConfig): Promise<RunResult> {
  const traces: TraceEvent[] = [];
  async function call(role: string, instruction: string, payload: unknown) {
    const started = Date.now();
    try {
      const output = await complete(provider, model.model, `${instruction}\n\nContext:\n${JSON.stringify(payload, null, 2)}`, model.temperature);
      traces.push({ role, input: payload, output, elapsedMs: Date.now() - started, valid: true });
      return output as Record<string, unknown>;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      traces.push({ role, input: payload, output: null, elapsedMs: Date.now() - started, valid: false, error: message });
      throw new Error(`${role}: ${message}`);
    }
  }

  const focal = await call("2.1 Focal Point Identifier", "Return { focalPoint: string }. State only the event or condition to explain; do not name a cause.", context(input));
  const focalPoint = String(focal.focalPoint || "");
  if (!focalPoint) throw new Error("Focal Point Identifier returned no focalPoint");

  const listA = await call("3A.1 List A", "Return { things: [{name, category, factIds}] }. Include only things explicitly mentioned in the incident. Every item needs at least one fact ID.", context(input));
  const explicitThings: Thing[] = Array.isArray(listA.things) ? (listA.things as Record<string, unknown>[]).map((thing, index) => ({ id: `A-${index + 1}`, name: String(thing.name), category: String(thing.category || "other"), provenance: "explicit" as const })) : input.things;
  const listB = await call("3A.2 List B", "Return { things: [{name, category, rationale}] }. Add only candidate things relevant to investigating the focal point. They are inferred/relevant, not report facts.", { focalPoint, incident: input.incident, listA: explicitThings });
  const inferredThings: Thing[] = Array.isArray(listB.things) ? (listB.things as Record<string, unknown>[]).map((thing, index) => ({ id: `B-${index + 1}`, name: String(thing.name), category: String(thing.category || "other"), provenance: "inferred" as const, rationale: String(thing.rationale || "") })) : [];
  const things = [...explicitThings, ...inferredThings];

  const focalNode: CausalNode = { id: "N-1", statement: focalPoint, depth: 0, status: "queued", factIds: [], notes: [] };
  const board: Board = { focalPoint, nodes: [focalNode], queue: [focalNode.id], version: 1 };
  let nodeNumber = 1;

  while (board.queue.length) {
    const nodeId = board.queue.shift()!;
    const node = board.nodes.find((item) => item.id === nodeId)!;
    const nodeContext = { node, board, facts: input.facts, things };
    const [keep, stop] = await Promise.all([
      call("5.1.1 Keep Digging", "Return { candidates: [{statement, factIds, rationale}] }. Name concrete immediate next causes to investigate. Do not say merely 'dig deeper'. Use only supplied fact IDs.", nodeContext),
      call("5.1.2 Stop Here", "Return { stop: boolean, reason: 'root_candidate'|'evidence_exhausted'|'outside_scope'|'duplicate'|'waiting_for_record', explanation: string }. Apply a legitimate stopping criterion independently.", nodeContext),
    ]);

    const controllability = await call("5.2 Controllability", "Return { actor: string|null, specificChange: string|null, explanation: string }. Name who could have changed this condition and exactly what; vague answers are null.", nodeContext);
    if (!controllability.actor || !controllability.specificChange) {
      await call("5.2 Control Gap", "Return { safeguard: string, gap: string, nextCause: string }. The condition may be uncontrollable; identify the protection that should have controlled exposure to it.", nodeContext);
    }

    const proposed = await call("5.5.1 Cause Proposer", "Return { causes: [{statement, factIds, rationale}] }. Propose the conditions that had to be present together for this node. Fact IDs must be supplied IDs only.", nodeContext);
    const causes = Array.isArray(proposed.causes) ? proposed.causes as Record<string, unknown>[] : [];
    const necessity = await call("5.5.2 Necessity Checker", "Return { checks: [{statement, necessary: boolean, explanation}] }. For every proposed cause, ask whether this event still happens without it.", { node, causes, facts: input.facts });
    const sufficiency = await call("5.5.3 Sufficiency Checker", "Return { sufficient: boolean, missing: string[], explanation: string }. Test whether the cause set is enough to explain the node, or name what is missing.", { node, causes, facts: input.facts });

    // 5.5.4 Why Referee (code): only retain candidates that appear in both proposal and keep-digging output.
    const keepCandidates = Array.isArray(keep.candidates) ? keep.candidates as Record<string, unknown>[] : [];
    const candidatePool = causes.length ? causes : keepCandidates;
    const nextStatements = new Set(candidatePool.map((cause) => String(cause.statement || "").trim()).filter(Boolean));
    const classified: CausalNode[] = [];
    for (const statement of nextStatements) {
      if (node.depth >= model.maxDepth) continue;
      const typeArea = await call("5.6 Type + Area", "Return { type: 'event'|'standing_condition', area: 'equipment'|'people'|'environment_area'|'procedures_work_process'|'organization_management_system' } for the candidate cause.", { statement, node, facts: input.facts });
      const retrieval = await call("5.7.1 Fact Retriever", "Return { factIds: string[] }. Retrieve only supplied facts relevant to the candidate by entity, fact type, then meaning.", { statement, facts: input.facts });
      const factIds = Array.isArray(retrieval.factIds) ? retrieval.factIds.map(String).filter((id) => input.facts.some((fact) => fact.id === id)) : [];
      const evidence = input.facts.filter((fact) => factIds.includes(fact.id));
      const [support, denial] = await Promise.all([
        call("5.7.2 Support", "Return { supports: boolean, factIds: string[], explanation: string }. Decide separately whether this evidence supports the cause.", { statement, evidence }),
        call("5.7.3 Denial", "Return { denies: boolean, factIds: string[], explanation: string }. Decide separately whether this evidence contradicts the cause.", { statement, evidence }),
      ]);
      // 5.7.4 Verdict Referee (code): denial wins; IDs must be retrieved IDs.
      const denialIds = Array.isArray(denial.factIds) ? denial.factIds.map(String).filter((id) => factIds.includes(id)) : [];
      const supportIds = Array.isArray(support.factIds) ? support.factIds.map(String).filter((id) => factIds.includes(id)) : [];
      const status = denial.denies && denialIds.length ? "disproven" : support.supports && supportIds.length ? "proven" : "waiting";
      const child: CausalNode = { id: `N-${++nodeNumber}`, statement, parentId: node.id, depth: node.depth + 1, status, type: typeArea.type === "event" ? "event" : "standing_condition", area: String(typeArea.area) as CausalNode["area"], factIds: status === "proven" ? supportIds : denialIds, notes: [String(support.explanation || ""), String(denial.explanation || "")] };
      board.nodes.push(child);
      classified.push(child);
      if (child.status === "proven") board.queue.push(child.id);
    }
    // 5.1.3 Node Referee (code): action nodes keep digging; lack of evidence parks.
    const isPersonAction = node.type === "event" && node.area === "people";
    if (isPersonAction || classified.some((child) => child.status === "proven")) node.status = "proven";
    else if (stop.stop) node.status = String(stop.reason) === "root_candidate" ? "root_candidate" : "stopped";
    else node.status = "waiting";
    board.version++;
    checkIntegrity(board);
  }

  const candidates = board.nodes.filter((node) => node.status === "root_candidate" || (node.status === "proven" && !board.nodes.some((child) => child.parentId === node.id && child.status === "proven")));
  for (const node of candidates) {
    const root = await call("6.1 Root Test", "Return { canWritePreventiveFix: boolean, explanation: string }. Test whether a specific preventive intervention can be written against this node.", { node, board, facts: input.facts });
    if (!root.canWritePreventiveFix) continue;
    const fix = await call("6.2 Fix Writer", "Return { action: string, changedCondition: string }. Write exactly what changes. Reject vague actions such as 'review the procedure'.", { node, board });
    const effectiveness = await call("6.3 Corrective Action Effectiveness Validation", "Return { preventsOrInterrupts: boolean, explanation: string }. Would this action, had it existed, prevent or materially interrupt the causal chain?", { node, action: fix.action, board });
    // 6.4 is code.
    node.status = effectiveness.preventsOrInterrupts ? "root_confirmed" : "proven";
    node.notes.push(String(fix.action || ""), String(effectiveness.explanation || ""));
  }
  checkIntegrity(board);
  return { id: randomUUID(), caseId: input.id, model, board, things, traces, startedAt: new Date().toISOString(), finishedAt: new Date().toISOString() };
}

function checkIntegrity(board: Board) {
  const seen = new Set<string>();
  for (const node of board.nodes) {
    const key = node.statement.trim().toLowerCase();
    if (seen.has(key)) node.notes.push("Integrity warning: duplicate causal statement");
    seen.add(key);
    if (node.parentId && !board.nodes.some((parent) => parent.id === node.parentId)) throw new Error(`Integrity failure: orphan node ${node.id}`);
    if (node.parentId === node.id) throw new Error(`Integrity failure: circular node ${node.id}`);
  }
}
