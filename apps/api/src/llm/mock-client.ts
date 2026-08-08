import type { PersonalityInput } from '@ai-hunger-games/contracts';
import type { 
  BatchedGeneratedAnswer, 
  BatchedGeneratedVote, 
  GenerateAnswersInput, 
  GenerateVotesInput, 
  LlmClient 
} from './types.js';

export class MockLlmClient implements LlmClient {
  public readonly provider = 'mock';
  public readonly model = 'mock-model';

  public async generateAnswers(input: GenerateAnswersInput): Promise<BatchedGeneratedAnswer[]> {
    return input.personalities.map((p) => ({
      id: p.id,
      answer: 'This is a mock answer. ' + 'Lorem ipsum '.repeat(10).trim(),
    }));
  }

  public async generateVotes(input: GenerateVotesInput): Promise<BatchedGeneratedVote[]> {
    return input.voters.map((v) => {
      const candidates = input.candidates.filter(c => c.id !== v.voterId);
      const chosen = candidates[Math.floor(Math.random() * candidates.length)]!;
      return {
        voterId: v.voterId,
        candidateKey: chosen.key,
        reason: 'This is a mock reason for the mock vote.',
      };
    });
  }

  public async generatePersonality(
    _eliminatedName: string,
    _remainingNames: string[],
  ): Promise<{ name: string; trait: string }> {
    return {
      name: 'The Synthesizer',
      trait: 'Integrates opposing viewpoints into a unified framework.',
    };
  }
}
