import { NextResponse } from 'next/server';
import { resumeTrack } from '@/src/server/repository';
import { z } from 'zod';

const resumeOptions = z.object({ taskId: z.string().min(1).optional(), pauseAfterTask: z.boolean().optional() }).strict()
  .refine(value => !value.pauseAfterTask || !!value.taskId, 'A taskId is required for single-task recovery.');

export async function POST(request: Request, context: { params: Promise<{ trackId: string }> }) {
  try {
    const text = await request.text();
    let body: unknown;
    try { body = text.trim() ? JSON.parse(text) : {}; }
    catch { return NextResponse.json({ error: 'Invalid recovery request JSON.' }, { status: 400 }); }
    const options = resumeOptions.safeParse(body);
    if (!options.success) return NextResponse.json({ error: options.error.message }, { status: 400 });
    return NextResponse.json(await resumeTrack((await context.params).trackId, options.data));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Resume failed.' }, { status: 500 });
  }
}
