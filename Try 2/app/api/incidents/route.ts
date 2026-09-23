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
    const body = await request.json() as { description?: unknown; modelIds?: unknown };
    if (typeof body.description !== 'string' || body.description.trim().length < 30) {
      return NextResponse.json({ error: 'A meaningful incident description is required.' }, { status: 400 });
    }
    if (!Array.isArray(body.modelIds) || !body.modelIds.length ||
      !body.modelIds.every((id) => typeof id === 'string')) {
      return NextResponse.json({ error: 'Select at least one valid model.' }, { status: 400 });
    }
    const id = await createIncident(body.description.trim(), [...new Set(body.modelIds)]);
    return NextResponse.json({ id }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to create investigation.' },
      { status: 500 },
    );
  }
}
