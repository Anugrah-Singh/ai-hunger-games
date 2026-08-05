import type { FastifyInstance } from 'fastify';
import {
  answersRequestSchema,
  votesRequestSchema,
  type AnswersRequest,
  type StatusResponse,
  type VotesRequest,
} from '@ai-hunger-games/contracts';
import type { AppConfig } from '../config/env.js';
import type { LlmClient } from '../llm/types.js';
import type { RequestCounter } from '../counter/types.js';
import { RequestCounterUnavailableError } from '../counter/types.js';
import { AppError } from '../errors/app-error.js';
import { parseBody } from '../http/validation.js';
import { consumeQuota, setQuotaHeaders } from '../http/quota.js';
import { secretsMatch } from '../http/security.js';
import { AnswerService } from '../services/answer-service.js';
import { VoteService } from '../services/vote-service.js';

export interface RouteDependencies {
  config: AppConfig;
  llm: LlmClient;
  counter: RequestCounter;
}

function toStatusResponse(status: Awaited<ReturnType<RequestCounter['status']>>): StatusResponse {
  return {
    trackingEnabled: status.trackingEnabled,
    requestsUsed: status.requestsUsed,
    requestLimit: status.requestLimit,
    remaining: status.remaining,
    disabled: status.disabled,
    percentageUsed: Number(((status.requestsUsed / status.requestLimit) * 100).toFixed(2)),
  };
}

export function registerRoutes(app: FastifyInstance, dependencies: RouteDependencies): void {
  const { config, llm, counter } = dependencies;
  const answers = new AnswerService(llm, config.AI_CONCURRENCY);
  const votes = new VoteService(llm, config.AI_CONCURRENCY);

  app.post('/api/answers', async (request, reply) => {
    const body = parseBody<AnswersRequest>(answersRequestSchema, request.body);
    await consumeQuota(counter, reply);
    const responses = await answers.generate(body.question, body.personalities);
    return reply.code(200).send({ responses });
  });

  app.post('/api/vote', async (request, reply) => {
    const body = parseBody<VotesRequest>(votesRequestSchema, request.body);
    await consumeQuota(counter, reply);
    const generatedVotes = await votes.generate(body.question, body.responses);
    return reply.code(200).send({ votes: generatedVotes });
  });

  app.get('/api/status', async (_request, reply) => {
    try {
      const status = await counter.status();
      setQuotaHeaders(reply, status);
      return reply.code(200).send(toStatusResponse(status));
    } catch (error) {
      if (error instanceof RequestCounterUnavailableError) {
        throw new AppError(503, 'REQUEST_TRACKING_UNAVAILABLE', error.message);
      }
      throw error;
    }
  });

  app.post(
    '/api/reset-counter',
    {
      config: {
        rateLimit: { max: 5, timeWindow: 60_000 },
      },
    },
    async (request, reply) => {
      const provided = request.headers['x-admin-key'];
      const key = Array.isArray(provided) ? provided[0] : provided;
      if (!secretsMatch(key, config.ADMIN_KEY)) {
        throw new AppError(401, 'UNAUTHORIZED', 'Invalid administrative credentials.');
      }

      try {
        await counter.reset();
      } catch (error) {
        if (error instanceof RequestCounterUnavailableError) {
          throw new AppError(503, 'REQUEST_TRACKING_UNAVAILABLE', error.message);
        }
        throw error;
      }

      return reply.code(200).send({ message: 'Counter reset successfully.' });
    },
  );

  app.get('/health', async (_request, reply) =>
    reply.code(200).send({
      status: 'healthy',
      timestamp: new Date().toISOString(),
    }),
  );

  app.get('/ready', async (_request, reply) => {
    try {
      await counter.status();
      return reply.code(200).send({
        status: 'ready',
        provider: llm.provider,
        model: llm.model,
      });
    } catch {
      return reply.code(503).send({ status: 'not-ready' });
    }
  });

  app.get('/ping', async (_request, reply) =>
    reply.code(200).send({
      status: 'alive',
      timestamp: Date.now(),
    }),
  );
}
