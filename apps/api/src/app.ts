import Fastify, { type FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import type { AppConfig } from './config/env.js';
import type { LlmClient } from './llm/types.js';
import type { RequestCounter } from './counter/types.js';
import { registerErrorHandling } from './http/error-handler.js';
import { registerRoutes } from './routes/register-routes.js';

export interface BuildAppOptions {
  config: AppConfig;
  llm: LlmClient;
  counter: RequestCounter;
}

export async function buildApp(options: BuildAppOptions): Promise<FastifyInstance> {
  const { config, llm, counter } = options;
  const app = Fastify({
    logger:
      config.NODE_ENV === 'test'
        ? false
        : { level: config.NODE_ENV === 'production' ? 'info' : 'debug' },
    trustProxy: config.TRUST_PROXY,
    bodyLimit: 64 * 1024,
    requestIdHeader: 'x-request-id',
  });

  await app.register(helmet, {
    contentSecurityPolicy: false,
  });

  await app.register(cors, {
    credentials: true,
    exposedHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Admin-Key'],
    origin(origin, callback) {
      if (!origin || config.WEB_ORIGINS.includes(origin)) {
        callback(null, true);
        return;
      }
      callback(null, false);
    },
  });

  await app.register(rateLimit, {
    global: true,
    max: config.HTTP_RATE_LIMIT,
    timeWindow: config.HTTP_RATE_WINDOW_MS,
  });

  registerErrorHandling(app);
  registerRoutes(app, { config, llm, counter });

  app.addHook('onClose', async () => {
    await counter.close();
  });

  await app.ready();
  return app;
}
