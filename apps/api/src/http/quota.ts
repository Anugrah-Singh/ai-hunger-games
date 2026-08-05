import type { FastifyReply } from 'fastify';
import { AppError } from '../errors/app-error.js';
import type { CounterDecision, CounterStatus, RequestCounter } from '../counter/types.js';
import { RequestCounterUnavailableError } from '../counter/types.js';

export function setQuotaHeaders(reply: FastifyReply, status: CounterStatus): void {
  reply.header('X-RateLimit-Limit', String(status.requestLimit));
  reply.header('X-RateLimit-Remaining', String(status.remaining));
}

export async function consumeQuota(
  counter: RequestCounter,
  reply: FastifyReply,
): Promise<CounterDecision> {
  try {
    const decision = await counter.consume();
    setQuotaHeaders(reply, decision);

    if (!decision.allowed) {
      throw new AppError(
        429,
        'REQUEST_LIMIT_REACHED',
        'The configured AI request limit has been reached.',
        { requestsUsed: decision.requestsUsed, requestLimit: decision.requestLimit },
      );
    }

    return decision;
  } catch (error) {
    if (error instanceof RequestCounterUnavailableError) {
      throw new AppError(503, 'REQUEST_TRACKING_UNAVAILABLE', error.message);
    }
    throw error;
  }
}
