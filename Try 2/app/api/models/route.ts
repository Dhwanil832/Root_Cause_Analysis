import { NextResponse } from 'next/server';

const OLLAMA_URL = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';

export async function GET() {
  const models = [{
    id: 'demo-field-analyst',
    name: 'Field Analyst',
    provider: 'builtin',
    detail: 'Built-in deterministic preview',
    available: true,
  }];
  try {
    const response = await fetch(OLLAMA_URL + '/api/tags', {
      signal: AbortSignal.timeout(1800),
      cache: 'no-store',
    });
    if (response.ok) {
      const payload = await response.json() as { models?: Array<{ name: string }> };
      for (const model of payload.models || []) {
        models.push({
          id: 'ollama:' + model.name,
          name: model.name,
          provider: 'ollama',
          detail: 'Ollama · local',
          available: true,
        });
      }
    }
  } catch {
    // An unavailable local Ollama server is a model status, not a page failure.
  }
  return NextResponse.json({
    models,
    ollamaUrl: OLLAMA_URL,
    apiProviderConfigured: Boolean(process.env.MODEL_PROVIDER_BASE_URL && process.env.MODEL_PROVIDER_API_KEY),
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json() as { tag?: unknown };
    if (typeof body.tag !== 'string' || !body.tag.trim() || body.tag.length > 180) {
      return NextResponse.json({ error: 'Enter a valid Ollama model tag.' }, { status: 400 });
    }
    const response = await fetch(OLLAMA_URL + '/api/pull', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: body.tag.trim(), stream: false }),
      signal: AbortSignal.timeout(20 * 60 * 1000),
    });
    if (!response.ok) {
      return NextResponse.json({ error: 'Ollama rejected the pull request.' }, { status: 502 });
    }
    return NextResponse.json({ ok: true, tag: body.tag.trim() });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unable to reach Ollama.' },
      { status: 502 },
    );
  }
}
