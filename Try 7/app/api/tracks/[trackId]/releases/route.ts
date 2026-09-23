import {NextResponse} from 'next/server';
import {z} from 'zod';
import {database,modelFromId} from '@/src/server/repository';
import {enqueueRevision} from '@/src/server/engine-repository';
import {readState,readJSON} from '@/src/engine/tasks/artifacts';
import type {RunRow} from '@/src/engine/tasks/d1-store';
import type {EngineInput} from '@/src/engine/types';

const schema=z.object({releaseId:z.string().trim().min(1),expectedVersion:z.number().int().positive(),
  answers:z.array(z.object({questionId:z.string().min(1),text:z.string().trim().min(1),responseStatus:z.enum(['answered','unknown','unavailable','partial']).optional()})).default([]),
  withdrawSourceIds:z.array(z.string()).default([])});
export async function POST(request:Request,context:{params:Promise<{trackId:string}>}) {
  try {
    const {trackId}=await context.params,body=schema.parse(await request.json()),db=database();
    const parent=await db.prepare('SELECT * FROM engine_runs WHERE track_id=? AND number=?').bind(trackId,body.expectedVersion).first<RunRow>();
    if(!parent||!['completed','partial'].includes(parent.status))throw Error('Release requires a published parent version.');
    const input=await readJSON<EngineInput>(db,parent.input_json),state=await readState(db,parent.state_json);
    if(body.answers.some(a=>!state?.questions.some(q=>q.id===a.questionId)))throw Error('Answer names a question outside this model track.');
    if(new Set(body.answers.map(a=>a.questionId)).size!==body.answers.length)throw Error('Duplicate question answers in release.');
    const known=new Set(input.documents.map(d=>d.id));
    if(body.withdrawSourceIds.some(id=>!known.has(id)))throw Error('Withdrawal names a source outside this track.');
    const documents=input.documents.filter(d=>!body.withdrawSourceIds.includes(d.id));
    const result=await enqueueRevision(db,trackId,input.incident,await modelFromId(input.model.id),documents,
      body.answers.map(a=>({...a,answeredAt:new Date().toISOString(),sourceId:`user-answer:${a.questionId}`})),
      {releaseId:body.releaseId,expectedVersion:body.expectedVersion});
    return NextResponse.json(result,{status:result.replayed?200:201});
  }catch(error){return NextResponse.json({error:error instanceof Error?error.message:'Release rejected.'},{status:409});}
}
