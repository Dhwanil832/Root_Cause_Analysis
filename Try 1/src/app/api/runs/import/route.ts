import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { saveRun } from "@/lib/server/db";
import type { RunResult } from "@/lib/types";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const submitted = await request.json() as Partial<RunResult>;
    const now = new Date().toISOString();
    const run = { ...submitted, id: submitted.id || randomUUID(), startedAt: submitted.startedAt || now, finishedAt: submitted.finishedAt || now } as RunResult;
    if (!run?.id || !run.caseId || !run.model?.model || !Array.isArray(run.traces) || !run.board) {
      return NextResponse.json({ error: "A complete managed RunResult is required" }, { status: 400 });
    }
    saveRun(run);
    return NextResponse.json(run, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Could not save managed run" }, { status: 500 });
  }
}
