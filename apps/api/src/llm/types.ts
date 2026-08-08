import type { PersonalityInput } from '@ai-hunger-games/contracts';

export interface VoteCandidate {
  key: string;
  id: number;
  answer: string;
}

export interface GenerateAnswersInput {
  question: string;
  personalities: PersonalityInput[];
}

export interface BatchedGeneratedAnswer {
  id: number;
  answer: string;
}

export interface VoterInput {
  voterId: number;
  voterAnswer: string;
  voterPersonality?: PersonalityInput;
}

export interface GenerateVotesInput {
  question: string;
  voters: VoterInput[];
  candidates: VoteCandidate[];
}

export interface BatchedGeneratedVote {
  voterId: number;
  candidateKey: string;
  reason: string;
}

export interface LlmClient {
  readonly provider: string;
  readonly model: string;
  generateAnswers(input: GenerateAnswersInput): Promise<BatchedGeneratedAnswer[]>;
  generateVotes(input: GenerateVotesInput): Promise<BatchedGeneratedVote[]>;
  generatePersonality(
    eliminatedName: string,
    remainingNames: string[],
  ): Promise<{ name: string; trait: string }>;
}
