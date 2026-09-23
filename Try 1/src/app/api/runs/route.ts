import { NextResponse } from "next/server";
import { getCase, listProviders, saveRun } from "@/lib/server/db";
import { runHarness } from "@/lib/server/harness";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const { providerId, model, temperature = 0.2, maxDepth = 3 } = await request.json();
    const provider = listProviders().find((item) => item.id === providerId && item.enabled);
    if (!provider) return NextResponse.json({ error: "Choose an enabled provider" }, { status: 400 });
    if (!model) return NextResponse.json({ error: "Model is required" }, { status: 400 });
    const item = getCase();
    const run = await runHarness(item, provider, { providerId, model, temperature: Number(temperature), maxDepth: Number(maxDepth) });
    saveRun(run);
    return NextResponse.json(run);
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Run failed" }, { status: 500 });
  }
}
