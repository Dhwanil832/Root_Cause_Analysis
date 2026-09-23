import { NextResponse } from 'next/server';
import { resumeTrack } from '@/src/server/repository';

export async function POST(_request: Request, context: { params: Promise<{ trackId: string }> }) {
  try {
    return NextResponse.json(await resumeTrack((await context.params).trackId));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Resume failed.' }, { status: 500 });
  }
}
