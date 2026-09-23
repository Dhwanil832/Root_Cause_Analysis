import { NextResponse } from 'next/server';
import { database, modelFromId } from '@/src/server/repository';
import { D1EngineStore } from '@/src/server/engine-repository';
import { runInvestigationTask } from '@/src/orchestrator/main-router';
import { loadDocumentMedia } from '@/src/server/document-media';

export async function POST(request: Request) {
  const key = process.env.RCA_WORKER_TOKEN;
  if (!key || request.headers.get('x-rca-worker-token') !== key) return NextResponse.json({ error: 'Worker authentication required.' }, { status: 403 });
  try {
    const result=await runInvestigationTask(new D1EngineStore(database()), modelFromId,undefined,
      input=>ids=>loadDocumentMedia(input.documents.filter(d=>ids.includes(d.id))));
    return NextResponse.json(result);
  }
  catch (error) { return NextResponse.json({ error: error instanceof Error ? error.message : String(error) }, { status: 500 }); }
}
