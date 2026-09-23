import { NextResponse } from 'next/server';
import { addTrackVersion } from '@/src/server/repository';

export async function POST(
  request: Request,
  context: { params: Promise<{ trackId: string }> },
) {
  try {
    const { trackId } = await context.params;
    const body = await request.json() as {
      questionId?: unknown;
      answer?: unknown;
      fileName?: unknown;
      fileKey?: unknown;
    };
    if (typeof body.questionId !== 'string' || typeof body.answer !== 'string' ||
      !body.answer.trim()) {
      return NextResponse.json({ error: 'Question and answer are required.' }, { status: 400 });
    }
    const result = await addTrackVersion(
      trackId,
      body.questionId,
      body.answer.trim(),
      {
        fileName: typeof body.fileName === 'string' ? body.fileName : undefined,
        fileKey: typeof body.fileKey === 'string' ? body.fileKey : undefined,
      },
    );
    if (!result) return NextResponse.json({ error: 'Model track not found.' }, { status: 404 });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to create version.' },
      { status: 500 },
    );
  }
}
