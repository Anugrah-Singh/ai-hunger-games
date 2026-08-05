import type { AppConfig } from '../config/env.js';
import { AiSdkLlmClient } from './ai-sdk-client.js';
import { MockLlmClient } from './mock-client.js';
import { createLanguageModel } from './provider-registry.js';
import type { LlmClient } from './types.js';

export function createLlmClient(config: AppConfig): LlmClient {
  if (config.LLM_PROVIDER === 'mock') return new MockLlmClient();
  return new AiSdkLlmClient(createLanguageModel(config), config);
}
