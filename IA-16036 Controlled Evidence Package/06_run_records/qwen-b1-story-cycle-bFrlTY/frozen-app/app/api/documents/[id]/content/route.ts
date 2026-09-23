import { NextResponse } from 'next/server';
import { getDocumentContent } from '@/src/server/repository';

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const result = await getDocumentContent(id);
    if (!result) return NextResponse.json({ error: 'Document not found.' }, { status: 404 });
    const headers = new Headers();
    result.body.writeHttpMetadata(headers);
    headers.set('content-type', result.document.contentType);
    headers.set('content-disposition', `inline; filename*=UTF-8''${encodeURIComponent(result.document.fileName)}`);
    headers.set('cache-control', 'private, max-age=300');
    headers.set('x-content-type-options', 'nosniff');
    return new Response(result.body.body, { headers });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to read document.' }, { status: 500 });
  }
}
