import { NextResponse } from 'next/server';
import { addHumanReviewVersion } from '@/src/server/repository';

const TARGET_TYPES = ['causal-node', 'causal-branch', 'corrective-action', 'document-observation'];
const ACTIONS = ['accept', 'reject', 'close-branch', 'approve'];

export async function POST(request: Request, context: { params: Promise<{ trackId: string }> }) {
  try {
    const { trackId } = await context.params;
    const body = await request.json() as Record<string, unknown>;
    if (!TARGET_TYPES.includes(String(body.targetType)) || !ACTIONS.includes(String(body.action)) || typeof body.targetId !== 'string') {
      return NextResponse.json({ error: 'A valid target and review action are required.' }, { status: 400 });
    }
    const result = await addHumanReviewVersion(trackId, {
      targetType: body.targetType as 'causal-node' | 'causal-branch' | 'corrective-action' | 'document-observation',
      targetId: body.targetId,
      action: body.action as 'accept' | 'reject' | 'close-branch' | 'approve',
      notes: typeof body.notes === 'string' ? body.notes : undefined,
      actor: typeof body.actor === 'string' ? body.actor : undefined,
      expectedVersion: typeof body.expectedVersion==='number'?body.expectedVersion:undefined,
    });
    if (!result) return NextResponse.json({ error: 'Model track not found.' }, { status: 404 });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to record the review decision.' }, { status: 500 });
  }
}
