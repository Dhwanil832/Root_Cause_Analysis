import { NextResponse } from 'next/server';
import { initializeTrack } from '@/src/server/repository';

export async function POST(_request: Request, context: { params: Promise<{ trackId: string }> }) {
  try {
    return NextResponse.json(await initializeTrack((await context.params).trackId, true));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Initialization failed.' }, { status: 500 });
  }
}
