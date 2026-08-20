import type { AppConfig } from './config/env.js';

export function createTestConfig(overrides: Partial<AppConfig> = {}): AppConfig {
  return {
    NODE_ENV: 'test',
    HOST: '127.0.0.1',
    PORT: 5000,
    WEB_ORIGINS: ['http://localhost:5173'],
    TRUST_PROXY: false,
    LLM_PROVIDER: 'mock',
    LLM_MODEL: 'test-model',
    AI_TIMEOUT_MS: 1_000,
    AI_MAX_RETRIES: 0,
    AI_CONCURRENCY: 2,
    AI_MAX_ANSWER_TOKENS: 140,
    AI_MAX_VOTE_TOKENS: 100,
    REQUEST_TRACKING_MODE: 'memory',
    REQUEST_LIMIT: 200,
    ADMIN_KEY: 'test-admin-key-that-is-long-enough',
    HTTP_RATE_LIMIT: 1_000,
    HTTP_RATE_WINDOW_MS: 60_000,
    ...overrides,
  };
}
