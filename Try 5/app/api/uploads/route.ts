import { NextResponse } from 'next/server';
import { addQuestionDocument } from '@/src/server/repository';

const MAX_FILE_BYTES = 16 * 1024 * 1024;

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get('file');
    const trackId = form.get('trackId');
    const questionId = form.get('questionId');
    if (!(file instanceof File) || typeof trackId !== 'string' || typeof questionId !== 'string') {
      return NextResponse.json({ error: 'File, track, and question are required.' }, { status: 400 });
    }
    if (file.size > MAX_FILE_BYTES) {
      return NextResponse.json({ error: 'File exceeds the 16 MB local limit.' }, { status: 413 });
    }
    const document = await addQuestionDocument(trackId, questionId, file,typeof form.get('answer')==='string'?String(form.get('answer')):'');
    if (!document) return NextResponse.json({ error: 'Model track not found.' }, { status: 404 });
    return NextResponse.json({
      document,
      fileKey: document.fileKey,
      fileName: document.fileName,
      contentType: document.contentType,
      size: document.size,
      queued: true,
    }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to upload file.' },
      { status: 500 },
    );
  }
}
