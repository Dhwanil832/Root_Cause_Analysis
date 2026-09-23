import { NextResponse } from 'next/server';
import {
  deleteProviderConfig,
  listProviderConfigs,
  saveProviderConfig,
  testProviderConfig,
} from '@/src/server/provider-vault';
import type { ProviderConfig } from '@/src/domain/types';

export async function GET() {
  try {
    return NextResponse.json({ providers: await listProviderConfigs() });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to load providers.' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json() as {
      action?: unknown;
      id?: unknown;
      name?: unknown;
      baseUrl?: unknown;
      apiMode?: unknown;
      modelIds?: unknown;
      apiKey?: unknown;
      enabled?: unknown;
    };
    if (body.action === 'test' && typeof body.id === 'string') {
      return NextResponse.json(await testProviderConfig(body.id));
    }
    if (typeof body.name !== 'string' || typeof body.baseUrl !== 'string' ||
      !['responses', 'chat-completions'].includes(String(body.apiMode)) ||
      !Array.isArray(body.modelIds) || !body.modelIds.every((item) => typeof item === 'string')) {
      return NextResponse.json({ error: 'Provider name, endpoint, API mode, and model IDs are required.' }, { status: 400 });
    }
    const provider = await saveProviderConfig({
      id: typeof body.id === 'string' ? body.id : undefined,
      name: body.name,
      baseUrl: body.baseUrl,
      apiMode: body.apiMode as ProviderConfig['apiMode'],
      modelIds: body.modelIds,
      apiKey: typeof body.apiKey === 'string' ? body.apiKey : undefined,
      enabled: typeof body.enabled === 'boolean' ? body.enabled : undefined,
    });
    return NextResponse.json({ provider }, { status: body.id ? 200 : 201 });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to save provider.' }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const body = await request.json() as { id?: unknown };
    if (typeof body.id !== 'string') return NextResponse.json({ error: 'Provider ID is required.' }, { status: 400 });
    await deleteProviderConfig(body.id);
    return NextResponse.json({ ok: true });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Unable to delete provider.' }, { status: 409 });
  }
}
