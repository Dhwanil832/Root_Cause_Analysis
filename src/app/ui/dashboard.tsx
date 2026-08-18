"use client";

import { useEffect, useState } from "react";
import type { ProviderConfig, RunResult } from "@/lib/types";

type Props = {
  initialCase: { id: string; name: string; incident: string; facts: { id: string; statement: string }[]; things: { id: string; name: string; provenance: string }[] };
  providers: ProviderConfig[];
  runs: RunResult[];
  roles: { id: string; section: string; name: string; kind: string; description: string }[];
};

export default function Dashboard({ initialCase, providers: initialProviders, runs: initialRuns, roles }: Props) {
  const [providers, setProviders] = useState(initialProviders);
  const [runs, setRuns] = useState(initialRuns);
  const [providerId, setProviderId] = useState(initialProviders[0]?.id ?? "");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("");
  const [selectedRun, setSelectedRun] = useState<RunResult | null>(initialRuns[0] ?? null);
  const [showProvider, setShowProvider] = useState(false);

  useEffect(() => {
    if (!providerId && providers[0]) setProviderId(providers[0].id);
  }, [providerId, providers]);

  async function startRun() {
    const provider = providers.find((item) => item.id === providerId);
    if (provider?.kind === "ollama") {
      setStatus("Checking whether the selected Ollama model is available locally…");
      const check = await fetch("/api/ollama/ensure", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ providerId, model, action: "check" }) });
      const availability = await check.json();
      if (!check.ok) { setStatus(`Ollama check failed: ${availability.error}`); return; }
      if (!availability.installed) {
        setStatus(`Downloading ${model} through local Ollama. This can take a few minutes…`);
        const pull = await fetch("/api/ollama/ensure", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ providerId, model, action: "pull" }) });
        if (!pull.ok || !pull.body) { setStatus(`Model download failed: ${await pull.text()}`); return; }
        const reader = pull.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            const progress = JSON.parse(line) as { status?: string; completed?: number; total?: number; error?: string };
            if (progress.error) { setStatus(`Model download failed: ${progress.error}`); return; }
            const percent = progress.total ? ` ${Math.round((progress.completed ?? 0) / progress.total * 100)}%` : "";
            setStatus(`${progress.status ?? "Downloading model"}${percent}`);
          }
          if (done) break;
        }
      }
    }
    setStatus("Running every selected logical role through the same model…");
    const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ providerId, model, temperature: 0.2, maxDepth: 3 }) });
    const payload = await response.json();
    if (!response.ok) { setStatus(`Run failed: ${payload.error}`); return; }
    setRuns((items) => [payload, ...items]); setSelectedRun(payload); setStatus("Run completed. The trace and causal board are saved.");
  }

  async function addProvider(form: FormData) {
    const response = await fetch("/api/providers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.fromEntries(form)) });
    const payload = await response.json();
    if (!response.ok) { setStatus(`Provider not saved: ${payload.error}`); return; }
    setProviders((items) => [...items, payload]); setProviderId(payload.id); setShowProvider(false);
  }

  return <main>
    <header><div><p className="eyebrow">MODEL-COMPARABLE RCA</p><h1>RCA Harness</h1><p className="muted">One methodology, one seeded case, one model at a time.</p></div><span className="pill">v1 · seeded evidence</span></header>
    <section className="hero"><div><p className="eyebrow">ACTIVE CASE</p><h2>{initialCase.name}</h2><p>{initialCase.incident}</p></div><div className="metric"><strong>{initialCase.facts.length}</strong><span>verified seeded facts</span></div><div className="metric"><strong>{initialCase.things.length}</strong><span>starting explicit things</span></div></section>
    <div className="grid">
      <section className="panel span2"><div className="panel-head"><div><p className="eyebrow">BASELINE RUN</p><h2>Run one model through the full harness</h2></div><button className="secondary" onClick={() => setShowProvider(true)}>Add provider</button></div>
        <div className="form-row"><label>Provider<select value={providerId} onChange={(event) => setProviderId(event.target.value)} onInput={(event) => setProviderId((event.target as HTMLSelectElement).value)}>{providers.map((provider) => <option key={provider.id} value={provider.id}>{provider.name} · {provider.kind}</option>)}</select></label><label>Model<input value={model} onChange={(event) => setModel(event.target.value)} onInput={(event) => setModel((event.target as HTMLInputElement).value)} placeholder="e.g. qwen3:8b or gpt-5.1" /></label><button className="primary" disabled={!providerId || !model || status.startsWith("Running")} onClick={startRun}>Run harness</button></div>
        <p className="hint">Keys stay out of the browser: configure an environment-variable name on the provider, such as <code>OPENAI_API_KEY</code>. If an Ollama model is missing, Run harness downloads it locally first. Ollama needs no key.</p>{status && <p className="status">{status}</p>}
      </section>
      <section className="panel"><p className="eyebrow">SELECTED SCOPE</p><h2>{roles.length} roles &amp; controls</h2><div className="role-list">{roles.map((role) => <div key={role.id}><span className={role.kind === "code" ? "code-tag" : "agent-tag"}>{role.section}</span><span>{role.name}</span></div>)}</div></section>
      <section className="panel span2"><p className="eyebrow">CAUSAL BOARD</p><h2>{selectedRun ? `Run ${selectedRun.id.slice(0, 8)}` : "No saved run yet"}</h2>{selectedRun ? <Board run={selectedRun} /> : <p className="muted">Choose a provider and model to produce the first board.</p>}</section>
      <section className="panel"><p className="eyebrow">RUN HISTORY</p>{runs.length ? <div className="run-list">{runs.map((run) => <button key={run.id} onClick={() => setSelectedRun(run)}><strong>{run.model.model}</strong><span>{new Date(run.startedAt).toLocaleString()}</span><span>{run.traces.length} trace events</span></button>)}</div> : <p className="muted">Runs are saved locally in SQLite.</p>}</section>
      <section className="panel span3"><p className="eyebrow">SEEDED FACT TABLE</p><div className="facts">{initialCase.facts.map((fact) => <div key={fact.id}><code>{fact.id}</code><span>{fact.statement}</span></div>)}</div></section>
    </div>
    {showProvider && <div className="modal"><form action={addProvider}><div className="panel"><p className="eyebrow">MODEL PROVIDER</p><h2>Add a provider</h2><label>Name<input name="name" required placeholder="OpenAI-compatible API" /></label><label>Type<select name="kind"><option value="openai_compatible">OpenAI-compatible</option><option value="ollama">Ollama</option></select></label><label>Base URL<input name="baseUrl" required placeholder="https://api.example.com/v1" /></label><label>API-key environment variable (optional)<input name="apiKeyEnvVar" placeholder="OPENAI_API_KEY" /></label><input type="hidden" name="enabled" value="true" /><div className="form-row"><button className="primary">Save provider</button><button type="button" className="secondary" onClick={() => setShowProvider(false)}>Cancel</button></div></div></form></div>}
  </main>;
}

function Board({ run }: { run: RunResult }) {
  return <><div className="board-summary"><span>Focal point: <strong>{run.board.focalPoint}</strong></span><span>{run.board.nodes.length} nodes · board v{run.board.version}</span></div><div className="nodes">{run.board.nodes.map((node) => <article key={node.id} className={`node ${node.status}`}><div><code>{node.id}</code><span className="status-tag">{node.status.replace("_", " ")}</span></div><strong>{node.statement}</strong><small>{node.type?.replace("_", " ") ?? "unclassified"} · {node.area?.replaceAll("_", " ") ?? "unassigned"}</small>{node.factIds.length > 0 && <small>Evidence: {node.factIds.join(", ")}</small>}</article>)}</div><details><summary>Run trace ({run.traces.length} steps)</summary><div className="trace">{run.traces.map((trace, index) => <div key={`${trace.role}-${index}`}><strong>{trace.role}</strong><span>{trace.valid ? `${trace.elapsedMs} ms` : `failed: ${trace.error}`}</span></div>)}</div></details></>;
}
