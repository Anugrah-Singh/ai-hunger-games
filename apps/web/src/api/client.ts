import {
  answersResponseSchema,
  apiErrorSchema,
  generatePersonalityResponseSchema,
  singleVoteResponseSchema,
  votesResponseSchema,
  type AnswersRequest,
  type AnswersResponse,
  type GeneratePersonalityRequest,
  type GeneratePersonalityResponse,
  type SingleVoteRequest,
  type SingleVoteResponse,
  type VotesRequest,
  type VotesResponse,
} from '@ai-hunger-games/contracts';
import type { ZodType } from 'zod';

class ApiClientError extends Error {
  public constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

const baseUrl = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/u, '');

async function readJson(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) return undefined;
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function request<T>(path: string, init: RequestInit, schema: ZodType<T>): Promise<T> {
  let response: Response;
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string>),
    };

    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiClientError('The API could not be reached. Check the configured API URL.');
  }

  const body = await readJson(response);
  if (!response.ok) {
    const parsed = apiErrorSchema.safeParse(body);
    throw new ApiClientError(
      parsed.success ? parsed.data.error.message : `Request failed with status ${response.status}.`,
      response.status,
      parsed.success ? parsed.data.error.code : undefined,
    );
  }

  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw new ApiClientError('The API returned an unexpected response format.', response.status);
  }
  return parsed.data;
}

export const api = {
  generateAnswers(payload: AnswersRequest, signal?: AbortSignal): Promise<AnswersResponse> {
    return request(
      '/api/answers',
      { method: 'POST', body: JSON.stringify(payload), ...(signal ? { signal } : {}) },
      answersResponseSchema,
    );
  },

  generateVotes(payload: VotesRequest, signal?: AbortSignal): Promise<VotesResponse> {
    return request(
      '/api/vote',
      { method: 'POST', body: JSON.stringify(payload), ...(signal ? { signal } : {}) },
      votesResponseSchema,
    );
  },

  generateSingleVote(
    payload: SingleVoteRequest,
    signal?: AbortSignal,
  ): Promise<SingleVoteResponse> {
    return request(
      '/api/vote/single',
      { method: 'POST', body: JSON.stringify(payload), ...(signal ? { signal } : {}) },
      singleVoteResponseSchema,
    );
  },

  generatePersonality(
    payload: GeneratePersonalityRequest,
    signal?: AbortSignal,
  ): Promise<GeneratePersonalityResponse> {
    return request(
      '/api/generate-personality',
      { method: 'POST', body: JSON.stringify(payload), ...(signal ? { signal } : {}) },
      generatePersonalityResponseSchema,
    );
  },
};

export function userMessageFor(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 429) return 'The configured AI request limit has been reached.';
    if (error.status === 503) return 'The AI service is temporarily unavailable.';
    return error.message;
  }
  return 'Something unexpected happened. Please try again.';
}
