import { NextResponse } from 'next/server';
import { z } from 'zod';
import { database } from '@/src/server/repository';
import type { RunRow } from '@/src/engine/tasks/d1-store';
import { readState } from '@/src/engine/tasks/artifacts';
import { digest } from '@/src/engine/identity';
import { activateReviewFormatting } from '@/src/server/review-formatting-migration';

const options=z.object({runId:z.string().uuid(),generation:z.number().int().nonnegative(),checkpointHash:z.string().min(1),
  recoverTaskIds:z.array(z.string().min(1)),reason:z.string().trim().min(1)}).strict();

// Operator action, following the existing local pause/resume API. All writes go
// through the app's D1 connection, never a competing native SQLite connection.
export async function POST(request:Request,context:{params:Promise<{trackId:string}>}) {
  const parsed=options.safeParse(await request.json().catch(()=>null));
  if(!parsed.success)return NextResponse.json({error:'Invalid formatting activation request.'},{status:400});
  const {trackId}=await context.params,body=parsed.data,db=database();
  const row=await db.prepare('SELECT * FROM engine_runs WHERE id=? AND track_id=?').bind(body.runId,trackId).first<RunRow>();
  if(!row||!['queued','running'].includes(row.status))return NextResponse.json({error:'Run is not active.'},{status:409});
  if(row.generation!==body.generation||row.lease_until!==0)return NextResponse.json({retryAtTaskBoundary:true},{status:409});
  if(body.checkpointHash!==await digest([row.input_json,row.state_json,row.snapshot_json]))
    return NextResponse.json({error:'Checkpoint hash changed.'},{status:409});
  const state=await readState(db,row.state_json);
  if(!state||state.reviewFormattingPolicy)return NextResponse.json({error:'Run is uninitialized or policy already set.'},{status:409});
  if(state.tasks.some(t=>t.status==='running'))return NextResponse.json({retryAtTaskBoundary:true},{status:409});
  const pauseReason='Operator-approved formatting guardrail activation at a completed task boundary.';
  const paused=await db.prepare("UPDATE engine_runs SET status='paused',pause_reason=?,lease=NULL,generation=generation+1,updated_at=? WHERE id=? AND generation=? AND status IN ('queued','running') AND lease_until=0")
    .bind(pauseReason,new Date().toISOString(),row.id,row.generation).run();
  if(!paused.meta.changes)return NextResponse.json({retryAtTaskBoundary:true},{status:409});
  try {
    return NextResponse.json(await activateReviewFormatting(db,row.id,row.generation+1,body.checkpointHash,body.reason,body.recoverTaskIds));
  } catch(error) {
    // Release only this action's temporary pause. Validation failure preserves
    // original state and cannot strand otherwise healthy independent work.
    await db.prepare("UPDATE engine_runs SET status='queued',pause_reason='',generation=generation+1,updated_at=? WHERE id=? AND status='paused' AND generation=? AND pause_reason=?")
      .bind(new Date().toISOString(),row.id,row.generation+1,pauseReason).run();
    return NextResponse.json({error:error instanceof Error?error.message:String(error)},{status:422});
  }
}
