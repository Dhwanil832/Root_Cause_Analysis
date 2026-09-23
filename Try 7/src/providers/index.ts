import { ollamaProvider } from './ollama';
import { openAiCompatibleProvider } from './openai-compatible';
import type { StageRequest, StageResponse } from './types';

const providers = [ollamaProvider, openAiCompatibleProvider];

export async function runProviderStage<T>(request: StageRequest<T>): Promise<StageResponse<T>> {
  const provider = providers.find((candidate) => candidate.supports(request.model));
  if (!provider) throw new Error(`No provider supports ${request.model.provider}.`);
  return provider.run(request);
}
