import type { PersonalityInput } from '@ai-hunger-games/contracts';

export interface VoteCandidate {
  key: string;
  id: number;
  answer: string;
}

export interface GenerateVoteInput {
  question: string;
  voterId: number;
  voterAnswer: string;
  candidates: VoteCandidate[];
}

export interface GeneratedVote {
  candidateKey: string;
  reason: string;
}

export interface LlmClient {
  readonly provider: string;
  readonly model: string;
  generateAnswer(question: string, personality: PersonalityInput): Promise<string>;
  generateVote(input: GenerateVoteInput): Promise<GeneratedVote>;
  generatePersonality(
    eliminatedName: string,
    remainingNames: string[],
  ): Promise<{ name: string; trait: string }>;
}
