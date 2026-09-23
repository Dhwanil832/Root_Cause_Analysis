import { NextResponse } from 'next/server';
import { z } from 'zod';
import { database } from '@/src/server/repository';
import { recoverPartialFrame } from '@/src/server/frame-recovery';
import type { RunRow } from '@/src/engine/tasks/d1-store';
import { digest } from '@/src/engine/identity';

const options = z.object({runId: z.string().uuid(), generation: z.number().int().nonnegative(),
  checkpointHash: z.string().regex(/^[a-f0-9]{64}$/), reason: z.string().trim().min(1)}).strict();
export async function GET(_request: Request, context: {params: Promise<{trackId: string}>}) {
  const {trackId} = await context.params;
  const row = await database().prepare('SELECT * FROM engine_runs WHERE track_id=? ORDER BY number DESC LIMIT 1').bind(trackId).first<RunRow>();
  if (!row) return NextResponse.json({error: 'Track run not found.'}, {status: 404});
  return NextResponse.json({runId: row.id, status: row.status, generation: row.generation, leaseUntil: row.lease_until,
    checkpointHash: await digest([row.input_json, row.state_json, row.snapshot_json])});
}
export async function POST(request: Request, context: {params: Promise<{trackId: string}>}) {
  const parsed = options.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({error: 'Invalid recovery request.'}, {status: 400});
  const {trackId} = await context.params, body = parsed.data, db = database();
  const row = await db.prepare('SELECT id FROM engine_runs WHERE id=? AND track_id=?').bind(body.runId, trackId).first();
  if (!row) return NextResponse.json({error: 'Run not found in this track.'}, {status: 404});
  try { return NextResponse.json(await recoverPartialFrame(db, body.runId, body.generation, body.checkpointHash, body.reason)); }
  catch (error) { return NextResponse.json({error: error instanceof Error ? error.message : String(error)}, {status: 409}); }
}
