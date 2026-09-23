import { z } from 'zod';
import { evidenceMessage, parseModelJson } from './json';
import type { ModelProvider, StageRequest, StageResponse } from './types';

export const openAiCompatibleProvider: ModelProvider = {
  supports: (model) => model.provider === 'openai-compatible',
  async run<T>(request: StageRequest<T>): Promise<StageResponse<T>> {
    const baseUrl = request.model.baseUrl || process.env.MODEL_PROVIDER_BASE_URL;
    const apiKey = request.model.apiKey || process.env.MODEL_PROVIDER_API_KEY;
    if (!baseUrl || !apiKey) throw new Error('The API provider is not configured.');
    const started = Date.now();
    const schema = z.toJSONSchema(request.schema, { target: 'draft-7' });
    const useResponses = request.model.apiMode === 'responses';
    const attempts: NonNullable<StageResponse<T>['attempts']> = [];
    let repair = '';
    let lastError: Error | null = null;
    for (let attempt = 1; attempt <= 2; attempt++) {
      const record: { attempt: number; raw: string; error?: string } = { attempt, raw: '' };
      attempts.push(record);
      try {
        const prompt = evidenceMessage(request.evidencePacket, repair);
        const responsesContent: Array<Record<string, unknown>> = [{ type: 'input_text', text: prompt }];
        const chatContent: Array<Record<string, unknown>> = [{ type: 'text', text: prompt }];
        for (const media of request.media || []) {
          const dataUrl = `data:${media.contentType};base64,${media.dataBase64}`;
          if (media.kind === 'image') {
            responsesContent.push({ type: 'input_image', image_url: dataUrl, detail: 'high' });
            chatContent.push({ type: 'image_url', image_url: { url: dataUrl, detail: 'high' } });
          } else if (useResponses) {
            responsesContent.push({ type: 'input_file', filename: media.fileName, file_data: dataUrl, detail: 'auto' });
          }
        }
        const response = await fetch(`${baseUrl.replace(/\/$/, '')}/${useResponses ? 'responses' : 'chat/completions'}`, {
          method: 'POST',
          headers: { authorization: `Bearer ${apiKey}`, 'content-type': 'application/json' },
          body: JSON.stringify(useResponses ? {
            model: request.model.name,
            store: false,
            instructions: request.systemPrompt,
            input: [{ role: 'user', content: responsesContent }],
            text: { format: { type: 'json_schema', name: request.schemaName, strict: true, schema } },
          } : {
              model: request.model.name,
              temperature: 0,
              messages: [
                { role: 'system', content: request.systemPrompt },
                { role: 'user', content: request.media?.length ? chatContent : prompt },
              ],
              response_format: { type: 'json_schema', json_schema: { name: request.schemaName, strict: true, schema } },
            }),
          signal: AbortSignal.timeout(180_000),
        });
        if (!response.ok) throw new Error(`API provider returned ${response.status}.`);
        const payload = await response.json() as {
          choices?: Array<{ message?: { content?: string }; finish_reason?: string }>;
          status?: string;
          output?: Array<{ content?: Array<{ type?: string; text?: string }> }>;
          output_text?: string;
          usage?: { prompt_tokens?: number; completion_tokens?: number; input_tokens?: number; output_tokens?: number };
        };
        const responsesText = payload.output_text || payload.output
          ?.flatMap((item) => item.content || [])
          .find((item) => item.type === 'output_text')?.text;
        record.raw = useResponses ? responsesText || '' : payload.choices?.[0]?.message?.content || '';
        if (payload.status === 'incomplete' || payload.choices?.[0]?.finish_reason === 'length') throw new Error('Output reached its limit before completion.');
        const parsed = request.schema.parse(parseModelJson(record.raw));
        const problems = request.validateOutput?.(parsed) || [];
        if (problems.length) throw new Error(`Output contract: ${problems.slice(0, 8).join('; ')}`);
        return {
          output: parsed,
          durationMs: Date.now() - started,
          engine: `api:${request.model.name}`,
          validation: attempt === 1 ? 'valid' : 'repaired',
          attempts,
          usage: {
            inputTokens: payload.usage?.input_tokens || payload.usage?.prompt_tokens,
            outputTokens: payload.usage?.output_tokens || payload.usage?.completion_tokens,
          },
        };
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('API stage failed.');
        record.error = lastError.message;
        repair = lastError.message.slice(0, 1200);
      }
    }
    throw Object.assign(lastError || new Error('API stage failed.'), { attempts });
  },
};
