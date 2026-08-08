import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { createOpenAI } from '@ai-sdk/openai';
import type { LanguageModel } from 'ai';
import type { AppConfig } from '../config/env.js';

function required(value: string | undefined, name: string): string {
  if (!value) throw new Error(`${name} is required for the selected LLM provider`);
  return value;
}

export function createLanguageModel(config: AppConfig): LanguageModel {
  switch (config.LLM_PROVIDER) {
    case 'openai': {
      const provider = createOpenAI({ apiKey: required(config.LLM_API_KEY, 'LLM_API_KEY') });
      return provider(config.LLM_MODEL);
    }
    case 'anthropic': {
      const provider = createAnthropic({ apiKey: required(config.LLM_API_KEY, 'LLM_API_KEY') });
      return provider(config.LLM_MODEL);
    }
    case 'google': {
      const provider = createGoogleGenerativeAI({
        apiKey: required(config.LLM_API_KEY, 'LLM_API_KEY'),
      });
      return provider(config.LLM_MODEL);
    }
    case 'mock':
      throw new Error('The mock provider does not create an AI SDK language model');
    default:
      throw new Error('Unsupported LLM provider');
  }
}
