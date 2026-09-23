import { NextResponse } from 'next/server';
import { createIncident, listHistory } from '@/src/server/repository';

export async function GET() {
  try {
    return NextResponse.json({ incidents: await listHistory() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to load history.' },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const contentType = request.headers.get('content-type') || '';
    let description: unknown;
    let modelIds: unknown;
    let files: File[] = [];
    let deferAnalysis = false;
    let title: string | undefined;
    if (contentType.includes('multipart/form-data')) {
      const form = await request.formData();
      description = form.get('description');
      deferAnalysis = form.get('deferAnalysis') === 'true';
      title = typeof form.get('title') === 'string' ? String(form.get('title')) : undefined;
      try { modelIds = JSON.parse(String(form.get('modelIds') || '[]')); }
      catch { modelIds = []; }
      files = form.getAll('files').filter((item): item is File => item instanceof File && item.size > 0);
    } else {
      const body = await request.json() as { description?: unknown; modelIds?: unknown; deferAnalysis?: boolean; title?: string };
      description = body.description;
      modelIds = body.modelIds;
      deferAnalysis = body.deferAnalysis === true;
      title = typeof body.title === 'string' ? body.title : undefined;
    }
    if (typeof description !== 'string' || description.trim().length < 30) {
      return NextResponse.json({ error: 'A meaningful incident description is required.' }, { status: 400 });
    }
    if (!Array.isArray(modelIds) || !modelIds.length || !modelIds.every((id) => typeof id === 'string')) {
      return NextResponse.json({ error: 'Select at least one valid model.' }, { status: 400 });
    }
    const id = await createIncident(description.trim(), [...new Set(modelIds)], files, { deferAnalysis, title });
    return NextResponse.json({ id }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to create investigation.' },
      { status: 500 },
    );
  }
}
