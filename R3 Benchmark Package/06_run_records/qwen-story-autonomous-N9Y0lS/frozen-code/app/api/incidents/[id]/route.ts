import { NextResponse } from 'next/server';
import { getIncident } from '@/src/server/repository';

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const incident = await getIncident(id);
    if (!incident) return NextResponse.json({ error: 'Incident not found.' }, { status: 404 });
    return NextResponse.json({ incident });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to load incident.' },
      { status: 500 },
    );
  }
}
