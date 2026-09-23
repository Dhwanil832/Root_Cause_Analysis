import type { ModelDescriptor } from '@/src/domain/types';
import type { StageRequest } from '@/src/providers/types';

// Explicit review-only configuration, not a model fallback or a retry policy.
// Qwen model-card Quickstart thinking profile, with a fixed evaluation seed:
// https://huggingface.co/Qwen/Qwen3.5-9B
export const QWEN_REVIEW_SAMPLING:NonNullable<StageRequest<unknown>['sampling']>={
  temperature:1,top_p:0.95,top_k:20,min_p:0,presence_penalty:1.5,repeat_penalty:1,seed:42,
};
export function reviewInference(model:ModelDescriptor,kind:string):{thinking:boolean;sampling?:StageRequest<unknown>['sampling']} {
  if(kind==='review'&&model.provider==='ollama'&&/^qwen3\.5(?::|$)/.test(model.id.replace(/^ollama:/,''))) {
    if(!model.capabilities?.includes('thinking'))throw Error('Qwen claim review requires a confirmed thinking capability. Refresh model discovery; no silent non-thinking fallback is used.');
    return {thinking:true,sampling:{...QWEN_REVIEW_SAMPLING}};
  }
  return {thinking:false};
}
