import { NextResponse } from 'next/server';
import { getStoryWorkspace,createStoryScenario,generateStoryRound,applyStoryRound } from '@/src/story-agent/repository';
type Context={params:Promise<{trackId:string}>};
export async function GET(_request:Request,context:Context) {
  try {return NextResponse.json(await getStoryWorkspace((await context.params).trackId));}
  catch(error) {return NextResponse.json({error:error instanceof Error?error.message:'Unable to load simulator.'},{status:400});}
}
export async function POST(request:Request,context:Context) {
  try {
    const {trackId}=await context.params;
    const body=await request.json() as {action?:string;scenario?:unknown;roundId?:unknown;strictCausal?:boolean;questionIds?:unknown};
    if(body.action==='create') return NextResponse.json(await createStoryScenario(trackId,body.scenario),{status:201});
    if(body.action==='generate') return NextResponse.json(await generateStoryRound(trackId,body.questionIds));
    if(body.action==='apply' && typeof body.roundId==='string') return NextResponse.json(await applyStoryRound(trackId,body.roundId,body.strictCausal === true));
    return NextResponse.json({error:'Unknown simulator action.'},{status:400});
  }catch(error) {return NextResponse.json({error:error instanceof Error?error.message:'Simulator request failed.'},{status:400});}
}
