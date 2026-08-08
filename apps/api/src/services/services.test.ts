import { describe, expect, it } from 'vitest';
import type {
  GenerateAnswersInput,
  GenerateVotesInput,
  BatchedGeneratedAnswer,
  BatchedGeneratedVote,
  LlmClient,
} from '../llm/types.js';
import { AnswerService } from './answer-service.js';
import { VoteService } from './vote-service.js';
import { PersonalityService } from './personality-service.js';

class FakeLlm implements LlmClient {
  public readonly provider = 'fake';
  public readonly model = 'fake-model';

  public async generateAnswers(input: GenerateAnswersInput): Promise<BatchedGeneratedAnswer[]> {
    return input.personalities.map((p) => ({
      id: p.id,
      answer: `${p.name} gives a detailed and useful answer.`,
    }));
  }

  public async generateVotes(input: GenerateVotesInput): Promise<BatchedGeneratedVote[]> {
    return input.voters.map((v) => {
      const candidate = input.candidates.find((c) => c.id !== v.voterId) || input.candidates[0];
      return {
        voterId: v.voterId,
        candidateKey: candidate!.key,
        reason: 'The reasoning is less convincing.',
      };
    });
  }

  public async generatePersonality(
    _eliminatedName: string,
    _remainingNames: string[],
  ): Promise<{ name: string; trait: string }> {
    return { name: 'The Visionary II', trait: 'Forward-looking perspective.' };
  }
}

describe('domain services', () => {
  it('generates answers', async () => {
    const service = new AnswerService(new FakeLlm(), 2);
    const answers = await service.generate('Question?', [
      { id: 3, name: 'Third', trait: 'Measured' },
      { id: 1, name: 'First', trait: 'Direct' },
    ]);

    expect(answers.map((answer) => answer.id)).toEqual([3, 1]);
    expect(answers[0].answer).toBe('Third gives a detailed and useful answer.');
  });

  it('uses fallback when answer generation is missing an id', async () => {
    const llm = new FakeLlm();
    llm.generateAnswers = async () => [];

    const service = new AnswerService(llm, 2);
    const answers = await service.generate('Question?', [
      { id: 1, name: 'The Philosopher', trait: 'Analytical' },
    ]);

    expect(answers).toHaveLength(1);
    expect(answers[0].id).toBe(1);
    expect(answers[0].answer).toBe('I have no answer.');
  });

  it('generates votes and maps candidate keys back to ids correctly', async () => {
    const llm = new FakeLlm();
    const service = new VoteService(llm, 2);

    const votes = await service.generate('Question?', [
      { id: 1, answer: 'One' },
      { id: 2, answer: 'Two' },
    ]);

    expect(votes).toHaveLength(2);
    expect(votes[0].voter).toBe(1);
    expect(votes[0].votedFor).toBe(2);
    expect(votes[1].voter).toBe(2);
    expect(votes[1].votedFor).toBe(1);
  });

  it('generates a new personality via PersonalityService', async () => {
    const service = new PersonalityService(new FakeLlm());
    const result = await service.generate('The Philosopher', ['The Pragmatist', 'The Optimist']);

    expect(result.name).toBe('The Visionary II');
    expect(result.trait).toBe('Forward-looking perspective.');
  });
});
