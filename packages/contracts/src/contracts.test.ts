import { describe, expect, it } from 'vitest';
import { answersRequestSchema, votesResponseSchema } from './index.js';

describe('API contracts', () => {
  it('accepts a valid answers request', () => {
    const result = answersRequestSchema.safeParse({
      question: 'What matters most?',
      personalities: [
        { id: 1, name: 'One', trait: 'Careful' },
        { id: 2, name: 'Two', trait: 'Bold' },
      ],
    });

    expect(result.success).toBe(true);
  });

  it('rejects duplicate personality IDs', () => {
    const result = answersRequestSchema.safeParse({
      question: 'What matters most?',
      personalities: [
        { id: 1, name: 'One', trait: 'Careful' },
        { id: 1, name: 'Two', trait: 'Bold' },
      ],
    });

    expect(result.success).toBe(false);
  });

  it('rejects a self-vote at the service boundary, not the transport shape', () => {
    const result = votesResponseSchema.safeParse({
      votes: [
        { voter: 1, votedFor: 1, reason: 'Invalid domain vote' },
        { voter: 2, votedFor: 1, reason: 'Different view' },
      ],
    });

    expect(result.success).toBe(true);
  });
});
