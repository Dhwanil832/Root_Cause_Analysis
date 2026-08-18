import { NextResponse } from "next/server";
import { saveProvider } from "@/lib/server/db";

export async function POST(request: Request) {
  const body = await request.json();
  if (!body.name || !body.baseUrl || !body.kind) return NextResponse.json({ error: "name, baseUrl, and kind are required" }, { status: 400 });
  const provider = { id: body.id || crypto.randomUUID(), name: String(body.name), kind: body.kind === "ollama" ? "ollama" as const : "openai_compatible" as const, baseUrl: String(body.baseUrl), apiKeyEnvVar: body.apiKeyEnvVar ? String(body.apiKeyEnvVar) : undefined, enabled: Boolean(body.enabled ?? true) };
  saveProvider(provider);
  return NextResponse.json(provider);
}
