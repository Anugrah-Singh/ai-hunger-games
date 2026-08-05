import type { PersonalityInput } from '@ai-hunger-games/contracts';
import type { GenerateVoteInput, GeneratedVote, LlmClient } from './types.js';

export class MockLlmClient implements LlmClient {
  public readonly provider = 'mock';
  public readonly model = 'deterministic-local-model';

  public async generateAnswer(question: string, personality: PersonalityInput): Promise<string> {
    return `${personality.name} considers “${question}” through a ${personality.trait.toLowerCase()} lens. The strongest response should stay clear, useful, and true to that perspective.`;
  }

  public async generateVote(input: GenerateVoteInput): Promise<GeneratedVote> {
    const candidate = input.candidates[0];
    if (!candidate) throw new Error('At least one candidate is required');

    return {
      candidateKey: candidate.key,
      reason: 'This answer is the least aligned with my perspective.',
    };
  }
}
