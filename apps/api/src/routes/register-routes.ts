import type { FastifyInstance } from 'fastify';
import {
  answersRequestSchema,
  generatePersonalityRequestSchema,
  singleVoteRequestSchema,
  votesRequestSchema,
  type AnswersRequest,
  type GeneratePersonalityRequest,
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
import { PersonalityService } from '../services/personality-service.js';
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
  const { config, llm: defaultLlm, counter } = dependencies;
  const defaultAnswers = new AnswerService(defaultLlm, config.AI_CONCURRENCY);
  const defaultVotes = new VoteService(defaultLlm, config.AI_CONCURRENCY);
  const defaultPersonalities = new PersonalityService(defaultLlm);

  const getServices = () => {
    return { answers: defaultAnswers, votes: defaultVotes, personalities: defaultPersonalities };
  };

  app.post('/api/answers', async (request, reply) => {
    const body = parseBody<AnswersRequest>(answersRequestSchema, request.body);
    await consumeQuota(counter, reply);
    const { answers } = getServices();
    const responses = await answers.generate(body.question, body.personalities);
    return reply.code(200).send({ responses });
  });

  app.post('/api/vote', async (request, reply) => {
    const body = parseBody<VotesRequest>(votesRequestSchema, request.body);
    await consumeQuota(counter, reply);
    const { votes } = getServices();
    const generatedVotes = await votes.generate(body.question, body.responses);
    return reply.code(200).send({ votes: generatedVotes });
  });

  app.post('/api/vote/single', async (request, reply) => {
    const body = parseBody(singleVoteRequestSchema, request.body);
    await consumeQuota(counter, reply);
    const { votes } = getServices();
    const generatedVote = await votes.generateSingle(
      body.question,
      body.voterId,
      body.responses,
      body.voterPersonality,
    );
    return reply.code(200).send({ vote: generatedVote });
  });

  app.post('/api/generate-personality', async (request, reply) => {
    const body = parseBody<GeneratePersonalityRequest>(
      generatePersonalityRequestSchema,
      request.body,
    );
    await consumeQuota(counter, reply);
    const { personalities } = getServices();
    const personality = await personalities.generate(body.eliminatedName, body.remainingNames);
    return reply.code(200).send({ personality });
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
        provider: defaultLlm.provider,
        model: defaultLlm.model,
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
