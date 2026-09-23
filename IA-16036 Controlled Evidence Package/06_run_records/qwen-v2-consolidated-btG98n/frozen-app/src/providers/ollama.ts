import { z } from 'zod';
import { evidenceMessage, parseModelJson } from './json';
import type { ModelProvider, StageRequest, StageResponse } from './types';
import { contextBudget, ContextOverflowError } from './context-budget';

const OLLAMA_URL = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';

interface OllamaPayload {
  message?: { content?: string };
  prompt_eval_count?: number;
  eval_count?: number;
  done_reason?: string;
}

const STAGE_OUTPUT_BUDGETS: Record<string, number> = {
  'story-answering': 6_400,
  'document-intelligence': 1_400,
  'incident-understanding': 3_200,
  'incident-structuring': 2_800,
  tagging: 1_600,
  'evidence-adjudication': 6_400,
  'question-broker': 5_200,
  'answer-fetching': 1_600,
  'evidence-processing': 6_400,
  'causal-analysis': 6_400,
  'causal-verification': 4_000,
  'corrective-actions': 3_200,
};

const HEAVY_STAGES = new Set([
  'story-answering',
  'evidence-adjudication',
  'evidence-processing',
  'causal-analysis',
]);

function stageTimeoutMs(stage: string) {
  if (HEAVY_STAGES.has(stage)) return 8 * 60 * 1000;
  if (stage === 'question-broker' || stage === 'causal-verification') return 6 * 60 * 1000;
  return 4 * 60 * 1000;
}

export const ollamaProvider: ModelProvider = {
  supports: (model) => model.provider === 'ollama',
  async run<T>(request: StageRequest<T>): Promise<StageResponse<T>> {
    const started = Date.now();
    const modelName = request.model.id.startsWith('ollama:')
      ? request.model.id.slice('ollama:'.length)
      : request.model.name;
    const jsonSchema = z.toJSONSchema(request.schema, { target: 'draft-7' });
    const managed = request.stage === 'causal-analysis' || request.stage === 'causal-verification';
    let repair = '';
    let lastError: Error | null = null;
    const attempts: NonNullable<StageResponse<T>['attempts']> = [];

    for (let attempt = 0; attempt < 2; attempt += 1) {
      const attemptRecord: { attempt: number; raw: string; error?: string } = { attempt: attempt + 1, raw: '' };
      attempts.push(attemptRecord);
      try {
        if (managed && !contextBudget(request.systemPrompt, request.evidencePacket, jsonSchema, request.stage, repair).fits) {
          throw new ContextOverflowError('Complete causal request exceeds the planning budget; partition the work without dropping evidence.');
        }
        const response = await fetch(`${OLLAMA_URL}/api/chat`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            model: modelName,
            stream: false,
            think: false,
            // These fields are supported by the installed Ollama 0.32.3. Do not
            // silently discard input or shift it away during causal generation.
            ...(managed ? { truncate: false, shift: false } : {}),
            format: jsonSchema,
            options: {
              temperature: 0,
              num_ctx: Number(process.env.OLLAMA_CONTEXT_LENGTH || 32_768),
              // Give evidence-heavy causal stages room to complete their JSON
              // while keeping classification and extraction stages bounded.
              num_predict: STAGE_OUTPUT_BUDGETS[request.stage] || 3_200,
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
          // The timeout must be long enough to accommodate the stage's declared
          // output budget on local hardware. A single global three-minute limit
          // made 5,200-6,400-token stages impossible for Qwen at ~26 tokens/sec.
          signal: AbortSignal.timeout(stageTimeoutMs(request.stage)),
        });
        if (!response.ok) {
          const detail = await response.text();
          if (managed && /context|too (?:large|long)|longer than|input length/i.test(detail)) {
            throw new ContextOverflowError(`Ollama refused an oversized causal request: ${detail}`);
          }
          throw new Error(`Ollama returned ${response.status}: ${detail.slice(0, 1200)}`);
        }
        const payload = await response.json() as OllamaPayload;
        attemptRecord.raw = payload.message?.content || '';
        if (payload.done_reason === 'length') throw new Error('Output reached its token limit before completion. Return a more concise complete JSON object.');
        const parsed = request.schema.safeParse(parseModelJson(payload.message?.content || ''));
        if (!parsed.success) {
          repair = parsed.error.issues.slice(0, 8).map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ');
          throw new Error(repair);
        }
        const problems = request.validateOutput?.(parsed.data) || [];
        if (problems.length) throw new Error(`Output contract: ${problems.slice(0, 8).join('; ')}`);
        return {
          output: parsed.data,
          durationMs: Date.now() - started,
          engine: `ollama:${modelName}`,
          validation: attempt === 0 ? 'valid' : 'repaired',
          usage: { inputTokens: payload.prompt_eval_count, outputTokens: payload.eval_count },
          attempts,
        };
      } catch (error) {
        // Retrying the same oversized request cannot repair it. The causal
        // operation planner catches this and divides the affected work only.
        if (error instanceof ContextOverflowError) throw Object.assign(error, { attempts });
        lastError = error instanceof Error ? error : new Error('Unknown Ollama error.');
        attemptRecord.error = lastError.message;
        repair = `${lastError.message.slice(0, 1200)} Return a complete, valid JSON object matching the schema. Keep explanations concise; do not omit required fields or invent evidence.`;
      }
    }
    throw Object.assign(lastError || new Error('Ollama stage failed.'), { attempts });
  },
};
