import { z } from 'zod';
import { evidenceMessage, parseModelJson } from './json';
import type { ModelProvider, StageRequest, StageResponse } from './types';
import { contextBudget, ContextOverflowError } from './context-budget';
import { StreamRepetitionGuard } from './stream-repetition';

const OLLAMA_URL = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';

interface OllamaPayload {
  message?: { content?: string; thinking?:string };
  prompt_eval_count?: number;
  eval_count?: number;
  done_reason?: string;
  done?: boolean;
  error?: string;
}

export const ollamaProvider: ModelProvider = {
  supports: (model) => model.provider === 'ollama',
  async run<T>(request: StageRequest<T>): Promise<StageResponse<T>> {
    const started = Date.now();
    const modelName = request.model.id.startsWith('ollama:')
      ? request.model.id.slice('ollama:'.length)
      : request.model.name;
    const jsonSchema = z.toJSONSchema(request.schema, { target: 'draft-7' });
    const managed = request.noTruncation || request.stage === 'causal-analysis' || request.stage === 'causal-verification';
    let repair = '';
    let lastError: Error | null = null;
    const attempts: NonNullable<StageResponse<T>['attempts']> = [];

    for (let attempt = 0; attempt < (request.maxAttempts ?? 2); attempt += 1) {
      const repetition = new StreamRepetitionGuard();
      const attemptRecord: NonNullable<StageResponse<T>['attempts']>[number] = { attempt: attempt + 1, raw: '',thinkingCharacters:0,repetition:repetition.stats };
      attempts.push(attemptRecord);
      const controller = new AbortController();
      // No default idle cutoff. Manual cancellation and actual context capacity
      // remain effective; slow generation is not an investigation failure.
      const idleMs=Number(process.env.OLLAMA_STREAM_IDLE_MS || 0);
      let idleTimer:ReturnType<typeof setTimeout>|undefined;
      const touch=()=>{clearTimeout(idleTimer);if(Number.isFinite(idleMs)&&idleMs>0)idleTimer=setTimeout(()=>controller.abort(new Error('Ollama stream stalled: no data before explicitly configured idle deadline.')),idleMs);};
      touch();
      let pendingCapture='',lastCapture=Date.now();
      const flush=async()=>{if(pendingCapture){const value=pendingCapture;pendingCapture='';await request.onChunk?.(value);lastCapture=Date.now();}};
      try {
        if (managed && !request.noTruncation && !contextBudget(request.systemPrompt, request.evidencePacket, jsonSchema, request.stage, repair).fits) {
          throw new ContextOverflowError('Complete causal request exceeds the planning budget; partition the work without dropping evidence.');
        }
        const response = await fetch(`${OLLAMA_URL}/api/chat`, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            model: modelName,
            stream: true,
            think: request.thinking ?? false,
            // These fields are supported by the installed Ollama 0.32.3. Do not
            // silently discard input or shift it away during causal generation.
            ...(managed ? { truncate: false, shift: false } : {}),
            format: jsonSchema,
            options: {
              temperature: 0,
              ...request.sampling,
              num_ctx: request.contextWindow || Number(process.env.OLLAMA_CONTEXT_LENGTH || 32_768),
              num_predict: request.noTruncation ? -1 : request.outputTokens ?? -1,
            },
            messages: [
              { role: 'system', content: request.systemPrompt },
              {
                role: 'user',
                // Ollama's format parameter constrains tokens; it is not a
                // substitute for showing the model the field meanings/choices.
                content: `${evidenceMessage(request.evidencePacket, repair)}\n\nRESPONSE CONTRACT (application instructions, not evidence):\n${JSON.stringify(jsonSchema)}`,
                ...(request.media?.some((media) => media.kind === 'image')
                  ? { images: request.media.filter((media) => media.kind === 'image').map((media) => media.dataBase64) }
                  : {}),
              },
            ],
          }),
          // Context capacity remains finite; manual cancellation revokes the lease.
          signal:request.signal ? AbortSignal.any([controller.signal,request.signal]) : controller.signal,
        });
        if (!response.ok) {
          const detail = await response.text();
          if (managed && /context|too (?:large|long)|longer than|input length/i.test(detail)) {
            throw new ContextOverflowError(`Ollama refused an oversized causal request: ${detail}`);
          }
          throw new Error(`Ollama returned ${response.status}: ${detail.slice(0, 1200)}`);
        }
        if(!response.body) throw new Error('Ollama returned no response stream.');
        const reader=response.body.getReader(),decoder=new TextDecoder();
        let buffer='',payload:OllamaPayload={},finished=false;
        const consume=async(line:string)=>{
          if(!line.trim())return;
          const part=JSON.parse(line) as OllamaPayload;
          if(part.error)throw new Error(`Ollama stream error: ${part.error}`);
          // Measure activity separately without putting private deliberation in
          // answer JSON, evidence, future context, or the user-facing trace.
          attemptRecord.thinkingCharacters=(attemptRecord.thinkingCharacters||0)+(part.message?.thinking||'').length;
          const content=part.message?.content||'';
          attemptRecord.raw+=content;pendingCapture+=content;
          // Observe duplicates without aborting. Only complete, validated output
          // can be applied; unfinished responses remain trace-only.
          repetition.push(content);
          if(pendingCapture.length>=4096||Date.now()-lastCapture>=2000)await flush();
          if(part.done){payload=part;finished=true;}
        };
        try {
          while(true){
            const chunk=await reader.read();if(chunk.done)break;
            touch();buffer+=decoder.decode(chunk.value,{stream:true});
            let newline:number;
            while((newline=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);await consume(line);}
          }
          buffer+=decoder.decode();if(buffer.trim())await consume(buffer);
        } finally { await reader.cancel().catch(()=>{});await flush(); }
        if(!finished)throw new Error('Ollama stream ended without a completion marker; partial output was preserved.');
        if (payload.done_reason === 'length') throw new Error('Output reached its token limit before completion. Return a more concise complete JSON object.');
        const parsed = request.schema.safeParse(parseModelJson(attemptRecord.raw));
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
          usage: { inputTokens: payload.prompt_eval_count, outputTokens: payload.eval_count,thinkingCharacters:attemptRecord.thinkingCharacters },
          attempts,
        };
      } catch (error) {
        // Retrying the same oversized request cannot repair it. The causal
        // operation planner catches this and divides the affected work only.
        if (error instanceof ContextOverflowError) throw Object.assign(error, { attempts });
        lastError = error instanceof Error ? error : new Error('Unknown Ollama error.');
        attemptRecord.error = lastError.message;
        repair = `${lastError.message.slice(0, 1200)} Return a complete, valid JSON object matching the schema. Keep explanations concise; do not omit required fields or invent evidence.`;
        if(request.signal?.aborted)throw Object.assign(lastError,{attempts});
      } finally {clearTimeout(idleTimer!);await flush();}
    }
    throw Object.assign(lastError || new Error('Ollama stage failed.'), { attempts });
  },
};
