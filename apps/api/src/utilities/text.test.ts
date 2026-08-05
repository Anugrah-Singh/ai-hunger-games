import { describe, expect, it } from 'vitest';

import { normalizeAnswer, normalizeReason } from './text.js';

describe('generated text normalization', () => {
  it('fixes known word-boundary generation mistakes', () => {
    expect(normalizeAnswer('We must not mis understand the nature of responsibility.')).toBe(
      'We must not misunderstand the nature of responsibility.',
    );
  });

  it('fixes missing punctuation spacing', () => {
    expect(normalizeAnswer('The result should be safer,faster, and more reliable.')).toBe(
      'The result should be safer, faster, and more reliable.',
    );
  });

  it('removes spaces before punctuation', () => {
    expect(normalizeAnswer('This matters , because decisions have consequences .')).toBe(
      'This matters, because decisions have consequences.',
    );
  });

  it('limits answers to the configured number of sentences', () => {
    expect(
      normalizeAnswer('First sentence. Second sentence! Third sentence? Fourth sentence.', 3),
    ).toBe('First sentence. Second sentence! Third sentence?');
  });

  it('provides a fallback for an empty voting reason', () => {
    expect(normalizeReason('   ')).toBe('Their answer is the least aligned with my perspective.');
  });
});
