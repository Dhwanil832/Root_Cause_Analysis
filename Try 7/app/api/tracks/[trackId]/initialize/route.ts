import { NextResponse } from 'next/server';
import { initializeTrack } from '@/src/server/repository';

export async function POST(request: Request, context: { params: Promise<{ trackId: string }> }) {
  try {
    const body=await request.json().catch(()=>({})) as {reviewAfterReading?:unknown};
    if(body.reviewAfterReading!==undefined&&typeof body.reviewAfterReading!=='boolean')return NextResponse.json({error:'reviewAfterReading must be a boolean.'},{status:400});
    return NextResponse.json(await initializeTrack((await context.params).trackId, true,{reviewAfterReading:body.reviewAfterReading as boolean|undefined}));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Initialization failed.' }, { status: 500 });
  }
}
