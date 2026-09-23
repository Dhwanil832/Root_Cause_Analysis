import type { ModelDescriptor } from '@/src/domain/types';
import type { StageRequest } from '@/src/providers/types';

// Explicit mode-specific configuration, not a model fallback or a retry policy.
// Qwen model-card thinking / general-instruct profiles, with a fixed evaluation seed:
// https://huggingface.co/Qwen/Qwen3.5-9B
export const QWEN_REVIEW_SAMPLING:NonNullable<StageRequest<unknown>['sampling']>={
  temperature:1,top_p:0.95,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42,
};
export const QWEN_INSTRUCT_SAMPLING:NonNullable<StageRequest<unknown>['sampling']>={
  temperature:0.7,top_p:0.8,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42,
};
export function reviewInference(model:ModelDescriptor,kind:string):{thinking:boolean;sampling?:StageRequest<unknown>['sampling']} {
  if(model.provider==='ollama'&&/^qwen3\.5(?::|$)/.test(model.id.replace(/^ollama:/,''))) {
    // Temperature-zero non-thinking inference produced an observed exact-record
    // loop. Use the published instruct profile; keep output/context uncapped.
    // Both profile and mode are already part of each request trace/cache key.
    if(kind!=='review') return {thinking:false,sampling:{...QWEN_INSTRUCT_SAMPLING}};
    if(!model.capabilities?.includes('thinking'))throw Error('Qwen claim review requires a confirmed thinking capability. Refresh model discovery; no silent non-thinking fallback is used.');
    return {thinking:true,sampling:{...QWEN_REVIEW_SAMPLING}};
  }
  return {thinking:false};
}
