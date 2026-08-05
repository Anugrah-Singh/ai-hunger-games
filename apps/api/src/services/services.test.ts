import { describe, expect, it, vi } from 'vitest';
import type { PersonalityInput } from '@ai-hunger-games/contracts';
import type { GenerateVoteInput, GeneratedVote, LlmClient } from '../llm/types.js';
import { AnswerService } from './answer-service.js';
import { VoteService } from './vote-service.js';

class FakeLlm implements LlmClient {
  public readonly provider = 'fake';
  public readonly model = 'fake-model';

  public async generateAnswer(_question: string, personality: PersonalityInput): Promise<string> {
    return `${personality.name} gives a detailed and useful answer.`;
  }

  public async generateVote(input: GenerateVoteInput): Promise<GeneratedVote> {
    const candidate = input.candidates.at(-1);
    if (!candidate) throw new Error('Missing candidate');
    return { candidateKey: candidate.key, reason: 'The reasoning is less convincing.' };
  }
}

describe('domain services', () => {
  it('preserves answer order while using concurrent generation', async () => {
    const service = new AnswerService(new FakeLlm(), 2);
    const answers = await service.generate('Question?', [
      { id: 3, name: 'Third', trait: 'Measured' },
      { id: 1, name: 'First', trait: 'Direct' },
    ]);

    expect(answers.map((answer) => answer.id)).toEqual([3, 1]);
  });

  it('logs failure and uses fallback when answer generation fails', async () => {
    const llm = new FakeLlm();
    const testError = new Error('Provider error');
    llm.generateAnswer = async () => {
      throw testError;
    };

    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const service = new AnswerService(llm, 2);
    const answers = await service.generate('Question?', [
      { id: 1, name: 'The Philosopher', trait: 'Analytical' },
    ]);

    expect(answers).toHaveLength(1);
    expect(answers[0].id).toBe(1);
    expect(answers[0].answer).toContain('This question reaches beneath the obvious answer');

    expect(spy).toHaveBeenCalledWith('LLM answer generation failed', {
      personalityId: 1,
      personalityName: 'The Philosopher',
      provider: 'fake',
      model: 'fake-model',
      error: testError,
    });

    spy.mockRestore();
  });

  it('never offers a voter their own answer', async () => {
    const observed: GenerateVoteInput[] = [];
    const llm = new FakeLlm();
    const original = llm.generateVote.bind(llm);
    llm.generateVote = async (input) => {
      observed.push(input);
      return original(input);
    };

    const service = new VoteService(llm, 2);
    await service.generate('Question?', [
      { id: 1, answer: 'One' },
      { id: 2, answer: 'Two' },
      { id: 3, answer: 'Three' },
    ]);

    for (const input of observed) {
      expect(input.candidates.some((candidate) => candidate.id === input.voterId)).toBe(false);
    }
  });

  it('uses a deterministic fallback for an invalid provider vote', async () => {
    const llm = new FakeLlm();
    llm.generateVote = async () => ({ candidateKey: 'UNKNOWN', reason: 'Invalid' });
    const service = new VoteService(llm, 3);

    const first = await service.generate('Question?', [
      { id: 1, answer: 'One' },
      { id: 2, answer: 'Two' },
      { id: 3, answer: 'Three' },
    ]);
    const second = await service.generate('Question?', [
      { id: 1, answer: 'One' },
      { id: 2, answer: 'Two' },
      { id: 3, answer: 'Three' },
    ]);

    expect(first).toEqual(second);
    expect(first.every((vote) => vote.voter !== vote.votedFor)).toBe(true);
  });
});
