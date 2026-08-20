import { z } from 'zod';

const emptyToUndefined = (value: unknown): unknown =>
  typeof value === 'string' && value.trim() === '' ? undefined : value;

const optionalString = z.preprocess(emptyToUndefined, z.string().trim().min(1).optional());
const optionalUrl = z.preprocess(emptyToUndefined, z.url().optional());

const booleanValue = (fallback: boolean) =>
  z.preprocess((value) => {
    if (value === undefined || value === '') return fallback;
    if (typeof value === 'boolean') return value;
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (['true', '1', 'yes', 'on'].includes(normalized)) return true;
      if (['false', '0', 'no', 'off'].includes(normalized)) return false;
    }
    return value;
  }, z.boolean());

const integerValue = (fallback: number, minimum: number, maximum: number) =>
  z.preprocess(
    (value) => (value === undefined || value === '' ? fallback : Number(value)),
    z.number().int().min(minimum).max(maximum),
  );

const envSchema = z
  .object({
    NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
    HOST: z.string().trim().min(1).default('0.0.0.0'),
    PORT: integerValue(5000, 1, 65_535),
    WEB_ORIGINS: z
      .string()
      .default('http://localhost:5173')
      .transform((value) =>
        value
          .split(',')
          .map((origin) => origin.trim())
          .filter(Boolean),
      ),
    TRUST_PROXY: booleanValue(false),

    LLM_PROVIDER: z
      .enum(['openai', 'anthropic', 'google', 'openai-compatible', 'mock'])
      .default('google'),
    LLM_MODEL: z.string().trim().min(1).default('gemini-3.5-flash-lite'),
    LLM_API_KEY: optionalString,

    AI_TIMEOUT_MS: integerValue(30_000, 1_000, 180_000),
    AI_MAX_RETRIES: integerValue(2, 0, 10),
    AI_CONCURRENCY: integerValue(3, 1, 8),
    AI_MAX_ANSWER_TOKENS: integerValue(1000, 32, 8192),
    AI_MAX_VOTE_TOKENS: integerValue(500, 32, 8192),

    REQUEST_TRACKING_MODE: z.enum(['disabled', 'memory']).default('memory'),
    REQUEST_LIMIT: integerValue(200, 1, 10_000_000),
    ADMIN_KEY: optionalString,

    HTTP_RATE_LIMIT: integerValue(60, 1, 100_000),
    HTTP_RATE_WINDOW_MS: integerValue(60_000, 1_000, 86_400_000),
  })
  .superRefine((config, context) => {
    if (['openai', 'anthropic', 'google'].includes(config.LLM_PROVIDER) && !config.LLM_API_KEY) {
      context.addIssue({
        code: 'custom',
        path: ['LLM_API_KEY'],
        message: `LLM_API_KEY is required for ${config.LLM_PROVIDER}`,
      });
    }

    if (
      config.NODE_ENV === 'production' &&
      config.REQUEST_TRACKING_MODE !== 'disabled' &&
      !config.ADMIN_KEY
    ) {
      context.addIssue({
        code: 'custom',
        path: ['ADMIN_KEY'],
        message: 'ADMIN_KEY is required in production when request tracking is enabled',
      });
    }
  });

export type AppConfig = z.infer<typeof envSchema>;

export function loadConfig(environment: NodeJS.ProcessEnv = process.env): AppConfig {
  const result = envSchema.safeParse(environment);

  if (!result.success) {
    const message = result.error.issues
      .map((issue) => `${issue.path.join('.') || 'environment'}: ${issue.message}`)
      .join('\n');
    throw new Error(`Invalid environment configuration:\n${message}`);
  }

  return result.data;
}
