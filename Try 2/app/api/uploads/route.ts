import { env } from 'cloudflare:workers';
import { NextResponse } from 'next/server';

const MAX_FILE_BYTES = 8 * 1024 * 1024;

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
      return NextResponse.json({ error: 'File exceeds the 8 MB local limit.' }, { status: 413 });
    }
    if (!env.FILES) throw new Error('The R2 binding FILES is unavailable.');
    const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '-');
    const key = 'evidence/' + trackId + '/' + questionId + '/' + crypto.randomUUID() + '-' + safeName;
    const bytes = await file.arrayBuffer();
    await env.FILES.put(key, bytes, {
      httpMetadata: { contentType: file.type || 'application/octet-stream' },
      customMetadata: { originalName: file.name, trackId, questionId },
    });
    const readable = ['text/plain', 'text/markdown', 'application/json'].includes(file.type);
    const excerpt = readable ? new TextDecoder().decode(bytes).slice(0, 12000) : '';
    return NextResponse.json({
      fileKey: key,
      fileName: file.name,
      contentType: file.type,
      size: file.size,
      excerpt,
    }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to upload file.' },
      { status: 500 },
    );
  }
}
