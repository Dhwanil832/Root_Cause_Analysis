import { NextResponse } from 'next/server';
import { database } from '@/src/server/repository';
import { D1EngineStore } from '@/src/engine/tasks/d1-store';

export async function POST(_request:Request,context:{params:Promise<{trackId:string}>}) {
  const {trackId}=await context.params,db=database();
  const row=await db.prepare("SELECT id FROM engine_runs WHERE track_id=? AND status IN ('queued','running') ORDER BY number LIMIT 1")
    .bind(trackId).first<{id:string}>();
  if(!row)return NextResponse.json({paused:false,error:'No active revision.'},{status:409});
  const paused=await new D1EngineStore(db).pause(row.id,'Paused by investigator. In-flight inference is cancelled on the next lease check; raw text remains preserved.');
  return NextResponse.json({paused,runId:row.id});
}
