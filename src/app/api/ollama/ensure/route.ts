import { NextResponse } from "next/server";
import { listProviders } from "@/lib/server/db";

function apiBase(baseUrl: string) {
  return `${baseUrl.replace(/\/$/, "").replace(/\/v1$/, "")}/api`;
}

function matchesInstalled(requested: string, installed: string) {
  const name = installed.toLowerCase();
  const target = requested.toLowerCase();
  return name === target || (target.endsWith(":latest") && name === target.slice(0, -7));
}

export async function POST(request: Request) {
  try {
    const { providerId, model, action = "check" } = await request.json() as { providerId?: string; model?: string; action?: "check" | "pull" };
    const provider = listProviders().find((item) => item.id === providerId && item.enabled);
    if (!provider || provider.kind !== "ollama") return NextResponse.json({ error: "Choose an enabled Ollama provider" }, { status: 400 });
    if (!model?.trim()) return NextResponse.json({ error: "Model is required" }, { status: 400 });
    const base = apiBase(provider.baseUrl);
    if (action === "check") {
      const response = await fetch(`${base}/tags`);
      if (!response.ok) throw new Error(`Ollama service returned ${response.status}`);
      const body = await response.json() as { models?: { name?: string; model?: string }[] };
      return NextResponse.json({ installed: (body.models ?? []).some((entry) => matchesInstalled(model, entry.name ?? entry.model ?? "")) });
    }
    const response = await fetch(`${base}/pull`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model, stream: true }) });
    if (!response.ok) throw new Error(`Ollama pull failed: ${await response.text()}`);
    return new Response(response.body, { headers: { "Content-Type": "application/x-ndjson", "Cache-Control": "no-cache" } });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Could not reach Ollama" }, { status: 502 });
  }
}
