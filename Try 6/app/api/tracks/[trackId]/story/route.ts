import { NextResponse } from 'next/server';
import { getStoryWorkspace,createStoryScenario,generateStoryRound,applyStoryRound } from '@/src/story-agent/repository';
import { database, modelFromId } from '@/src/server/repository';
import { latestInput } from '@/src/server/engine-repository';
import { storyWorkerStep } from '@/src/story-agent/worker';
type Context={params:Promise<{trackId:string}>};
export async function GET(_request:Request,context:Context) {
  try {return NextResponse.json(await getStoryWorkspace((await context.params).trackId));}
  catch(error) {return NextResponse.json({error:error instanceof Error?error.message:'Unable to load simulator.'},{status:400});}
}
export async function POST(request:Request,context:Context) {
  try {
    const {trackId}=await context.params;
    const body=await request.json() as {action?:string;scenario?:unknown;roundId?:unknown;strictCausal?:boolean;questionIds?:string[];sourceIds?:string[];documents?:{sourceId:string;questionId:string}[];approvedQuestionIds?:string[]};
    if(body.action==='create') return NextResponse.json(await createStoryScenario(trackId,body.scenario),{status:201});
    if(body.action==='generate') return NextResponse.json(await generateStoryRound(trackId,body.questionIds,body.sourceIds));
    if(body.action==='step' && typeof body.roundId==='string') {
      const workspace=await getStoryWorkspace(trackId);
      if(!workspace.rounds.some(r=>r.id===body.roundId))throw Error('Round does not belong to this model track.');
      const current=await latestInput(database(),trackId);
      if(current && !['completed','partial'].includes(current.row.status))throw Error('Complete the RCA run before executing the separate story batch.');
      return NextResponse.json(await storyWorkerStep(database(),modelFromId,undefined,body.roundId));
    }
    if(body.action==='apply' && typeof body.roundId==='string') return NextResponse.json(await applyStoryRound(trackId,body.roundId,body.strictCausal === true,body.documents,body.approvedQuestionIds));
    return NextResponse.json({error:'Unknown simulator action.'},{status:400});
  }catch(error) {return NextResponse.json({error:error instanceof Error?error.message:'Simulator request failed.'},{status:400});}
}
