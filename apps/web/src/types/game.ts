import type { Answer, PersonalityInput, Vote } from '@ai-hunger-games/contracts';

export interface PersonalityTheme {
  avatar: string;
  border: string;
  text: string;
  glow: string;
}

export interface Personality extends PersonalityInput {
  alive: boolean;
  theme: PersonalityTheme;
}

export type GamePhase =
  | 'input'
  | 'generatingAnswers'
  | 'reviewAnswers'
  | 'generatingVotes'
  | 'reviewVotes'
  | 'roundComplete'
  | 'tieBreak'
  | 'eliminated'
  | 'winner';

export interface GameState {
  phase: GamePhase;
  generationNumber: number;
  roundInGeneration: number;
  cumulativeScores: Record<number, number>;
  nextPersonalityId: number;
  round: number;
  question: string;
  personalities: Personality[];
  answers: Answer[];
  votes: Vote[];
  eliminatedId: number | undefined;
  tiedIds: number[];
  error: string | undefined;
}
