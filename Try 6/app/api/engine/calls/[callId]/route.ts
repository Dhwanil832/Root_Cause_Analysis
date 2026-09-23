import { NextResponse } from 'next/server';
import { database } from '@/src/server/repository';
import { readJSON } from '@/src/engine/tasks/artifacts';

export async function GET(_request:Request,context:{params:Promise<{callId:string}>}) {
  const {callId}=await context.params,db=database();
  const row=await db.prepare('SELECT * FROM engine_calls WHERE id=?').bind(callId)
    .first<{request_json:string|null;result_json:string|null;[key:string]:unknown}>();
  if(!row)return NextResponse.json({error:'Call not found.'},{status:404});
  const chunks=await db.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').bind(`stream:${callId}`).all<{content:string}>();
  return NextResponse.json({...row,request:row.request_json?await readJSON(db,row.request_json):null,
    result:row.result_json?await readJSON(db,row.result_json):null,raw:chunks.results.map(c=>c.content).join(''),request_json:undefined,result_json:undefined});
}
