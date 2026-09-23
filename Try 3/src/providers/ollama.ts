import { z } from 'zod';
import { evidenceMessage, parseModelJson } from './json';
import type { ModelProvider, StageRequest, StageResponse } from './types';

const OLLAMA_URL = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';

interface OllamaPayload {
  message?: { content?: string };
  prompt_eval_count?: number;
  eval_count?: number;
}

export const ollamaProvider: ModelProvider = {
  supports: (model) => model.provider === 'ollama',
  async run<T>(request: StageRequest<T>): Promise<StageResponse<T>> {
    const started = Date.now();
    const modelName = request.model.id.startsWith('ollama:')
      ? request.model.id.slice('ollama:'.length)
      : request.model.name;
    const jsonSchema = z.toJSONSchema(request.schema, { target: 'draft-7' });
    let repair = '';
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const response = await fetch(`${OLLAMA_URL}/api/chat`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            model: modelName,
            stream: false,
            think: false,
            format: jsonSchema,
            options: {
              temperature: 0,
              num_ctx: Number(process.env.OLLAMA_CONTEXT_LENGTH || 16_384),
              num_predict: 2_400,
            },
            messages: [
              { role: 'system', content: request.systemPrompt },
              {
                role: 'user',
                content: evidenceMessage(request.evidencePacket, repair),
                ...(request.media?.some((media) => media.kind === 'image')
                  ? { images: request.media.filter((media) => media.kind === 'image').map((media) => media.dataBase64) }
                  : {}),
              },
            ],
          }),
          signal: AbortSignal.timeout(180_000),
        });
        if (!response.ok) throw new Error(`Ollama returned ${response.status}.`);
        const payload = await response.json() as OllamaPayload;
        const parsed = request.schema.safeParse(parseModelJson(payload.message?.content || ''));
        if (!parsed.success) {
          repair = parsed.error.issues.slice(0, 8).map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ');
          throw new Error(repair);
        }
        return {
          output: parsed.data,
          durationMs: Date.now() - started,
          engine: `ollama:${modelName}`,
          validation: attempt === 0 ? 'valid' : 'repaired',
          usage: { inputTokens: payload.prompt_eval_count, outputTokens: payload.eval_count },
        };
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Unknown Ollama error.');
      }
    }
    throw lastError || new Error('Ollama stage failed.');
  },
};
