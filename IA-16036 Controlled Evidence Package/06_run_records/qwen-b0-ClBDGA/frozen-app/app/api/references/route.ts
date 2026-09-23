import { NextResponse } from 'next/server';
import { addReferenceDocument, listReferenceDocuments } from '@/src/server/repository';

export async function GET() {
  try {
    return NextResponse.json({ documents: await listReferenceDocuments() });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to load the reference library.' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get('file');
    if (!(file instanceof File)) return NextResponse.json({ error: 'Choose a document.' }, { status: 400 });
    const document = await addReferenceDocument(
      file,
      String(form.get('title') || file.name),
      String(form.get('plant') || 'General'),
      String(form.get('revision') || '1'),
    );
    return NextResponse.json({ document }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to add the reference document.' }, { status: 500 });
  }
}
