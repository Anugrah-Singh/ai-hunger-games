import { describe, expect, it } from 'vitest';
import { buildApp } from './app.js';
import { MemoryRequestCounter } from './counter/memory-counter.js';
import { MockLlmClient } from './llm/mock-client.js';
import { createTestConfig } from './test-helpers.js';

async function createTestApp(limit = 200) {
  const config = createTestConfig({ REQUEST_LIMIT: limit });
  return buildApp({
    config,
    llm: new MockLlmClient(),
    counter: new MemoryRequestCounter(limit),
  });
}

describe('HTTP API', () => {
  it('generates typed personality answers', async () => {
    const app = await createTestApp();
    const response = await app.inject({
      method: 'POST',
      url: '/api/answers',
      payload: {
        question: 'What makes a good decision?',
        personalities: [
          { id: 1, name: 'The Analyst', trait: 'Data-driven' },
          { id: 2, name: 'The Empath', trait: 'Understanding' },
        ],
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().responses).toHaveLength(2);
    expect(response.headers['x-ratelimit-remaining']).toBe('199');
    await app.close();
  });

  it('generates anonymous typed votes', async () => {
    const app = await createTestApp();
    const response = await app.inject({
      method: 'POST',
      url: '/api/vote',
      payload: {
        question: 'Which answer is least convincing?',
        responses: [
          { id: 1, answer: 'Evidence should guide the decision.' },
          { id: 2, answer: 'Human impact should guide the decision.' },
        ],
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().votes).toHaveLength(2);
    expect(
      response
        .json()
        .votes.every((vote: { voter: number; votedFor: number }) => vote.voter !== vote.votedFor),
    ).toBe(true);
    await app.close();
  });

  it('returns a safe error envelope for malformed JSON', async () => {
    const app = await createTestApp();
    const response = await app.inject({
      method: 'POST',
      url: '/api/answers',
      headers: { 'content-type': 'application/json' },
      payload: '{"question":',
    });

    expect(response.statusCode).toBe(400);
    expect(response.json().error.code).toBe('INVALID_JSON');
    await app.close();
  });

  it('rejects duplicate IDs with a common validation envelope', async () => {
    const app = await createTestApp();
    const response = await app.inject({
      method: 'POST',
      url: '/api/answers',
      payload: {
        question: 'Question?',
        personalities: [
          { id: 1, name: 'One', trait: 'Calm' },
          { id: 1, name: 'Two', trait: 'Bold' },
        ],
      },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json().error.code).toBe('VALIDATION_ERROR');
    await app.close();
  });

  it('returns 429 after the configured logical request limit', async () => {
    const app = await createTestApp(1);
    const payload = {
      question: 'Question?',
      personalities: [
        { id: 1, name: 'One', trait: 'Calm' },
        { id: 2, name: 'Two', trait: 'Bold' },
      ],
    };

    expect((await app.inject({ method: 'POST', url: '/api/answers', payload })).statusCode).toBe(
      200,
    );
    const blocked = await app.inject({ method: 'POST', url: '/api/answers', payload });
    expect(blocked.statusCode).toBe(429);
    expect(blocked.json().error.code).toBe('REQUEST_LIMIT_REACHED');
    await app.close();
  });

  it('resets the request counter with the admin key', async () => {
    const app = await createTestApp(1);
    const reset = await app.inject({
      method: 'POST',
      url: '/api/reset-counter',
      headers: { 'x-admin-key': 'test-admin-key-that-is-long-enough' },
    });

    expect(reset.statusCode).toBe(200);
    const status = await app.inject({ method: 'GET', url: '/api/status' });
    expect(status.json().requestsUsed).toBe(0);
    await app.close();
  });

  it('uses a JSON 404 envelope', async () => {
    const app = await createTestApp();
    const response = await app.inject({ method: 'GET', url: '/missing' });
    expect(response.statusCode).toBe(404);
    expect(response.json().error.code).toBe('NOT_FOUND');
    await app.close();
  });
});
