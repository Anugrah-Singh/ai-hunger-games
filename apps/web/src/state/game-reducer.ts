import type { Answer, Vote } from '@ai-hunger-games/contracts';
import { INITIAL_PERSONALITIES } from '../data/personalities.js';
import type { GamePhase, GameState, Personality } from '../types/game.js';

export const ROUNDS_PER_GENERATION = 8;

export type GameAction =
  | { type: 'questionChanged'; question: string }
  | { type: 'answersRequested' }
  | { type: 'answersReceived'; answers: Answer[] }
  | { type: 'votesRequested' }
  | { type: 'votesReceived'; votes: Vote[] }
  | { type: 'resolveVotes' }
  | { type: 'breakTie'; id: number }
  | { type: 'nextRound' }
  | { type: 'personalityReplaced'; personality: Personality }
  | { type: 'failed'; message: string; resumeAt: GamePhase }
  | { type: 'dismissError' }
  | { type: 'reset' };

export function createInitialState(): GameState {
  return {
    phase: 'input',
    generationNumber: 1,
    roundInGeneration: 1,
    cumulativeScores: {},
    nextPersonalityId: 9,
    round: 1,
    question: '',
    personalities: INITIAL_PERSONALITIES.map((personality) => ({ ...personality, alive: true })),
    answers: [],
    votes: [],
    tiedIds: [],
    eliminatedId: undefined,
    error: undefined,
  };
}

export function alivePersonalities(state: GameState): Personality[] {
  return state.personalities.filter((personality) => personality.alive);
}

export function voteCount(votes: Vote[], personalityId: number): number {
  return votes.filter((vote) => vote.votedFor === personalityId).length;
}

export function cumulativeScore(scores: Record<number, number>, personalityId: number): number {
  return scores[personalityId] ?? 0;
}

function eliminate(state: GameState, id: number): GameState {
  const target = state.personalities.find(
    (personality) => personality.id === id && personality.alive,
  );
  if (!target) return state;

  const personalities = state.personalities.map((personality) =>
    personality.id === id ? { ...personality, alive: false } : personality,
  );
  const remaining = personalities.filter((personality) => personality.alive);

  return {
    ...state,
    personalities,
    eliminatedId: id,
    tiedIds: [],
    roundInGeneration: 0,
    cumulativeScores: {},
    phase: remaining.length === 1 ? 'winner' : 'eliminated',
  };
}

function resolveVotes(state: GameState): GameState {
  const alive = alivePersonalities(state);
  if (state.votes.length !== alive.length) {
    return { ...state, error: 'A complete vote set is required before elimination.' };
  }

  // Accumulate this round's positive votes into cumulative scores
  const updatedScores = { ...state.cumulativeScores };
  for (const vote of state.votes) {
    updatedScores[vote.votedFor] = (updatedScores[vote.votedFor] ?? 0) + 1;
  }
  const stateWithScores = { ...state, cumulativeScores: updatedScores };

  // Not yet at the end of the 8-round generation window — proceed to roundComplete phase
  if (state.roundInGeneration < ROUNDS_PER_GENERATION) {
    return { ...stateWithScores, phase: 'roundComplete' };
  }

  // End of 8-round generation window — eliminate the lowest scorer among alive personalities
  const scores = new Map(alive.map((personality) => [personality.id, updatedScores[personality.id] ?? 0]));
  const minimum = Math.min(...scores.values());
  const tiedIds = [...scores.entries()]
    .filter(([, score]) => score === minimum)
    .map(([id]) => id);

  if (tiedIds.length > 1) return { ...stateWithScores, tiedIds, phase: 'tieBreak' };
  const eliminatedId = tiedIds[0];
  return eliminatedId === undefined ? stateWithScores : eliminate(stateWithScores, eliminatedId);
}

export function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'questionChanged':
      return state.phase === 'input'
        ? { ...state, question: action.question, error: undefined }
        : state;
    case 'answersRequested':
      return {
        ...state,
        phase: 'generatingAnswers',
        answers: [],
        votes: [],
        tiedIds: [],
        eliminatedId: undefined,
        error: undefined,
      };
    case 'answersReceived':
      return { ...state, answers: action.answers, phase: 'reviewAnswers', error: undefined };
    case 'votesRequested':
      return { ...state, votes: [], phase: 'generatingVotes', error: undefined };
    case 'votesReceived':
      return { ...state, votes: action.votes, phase: 'reviewVotes', error: undefined };
    case 'resolveVotes':
      return resolveVotes(state);
    case 'breakTie':
      return state.tiedIds.includes(action.id) ? eliminate(state, action.id) : state;
    case 'nextRound':
      return {
        ...state,
        phase: 'input',
        round: state.round + 1,
        roundInGeneration: state.roundInGeneration + 1,
        question: '',
        answers: [],
        votes: [],
        tiedIds: [],
        eliminatedId: undefined,
        error: undefined,
      };
    case 'personalityReplaced': {
      const personalities = state.personalities.map((personality) =>
        personality.id === state.eliminatedId ? action.personality : personality,
      );
      return {
        ...state,
        personalities,
        nextPersonalityId: state.nextPersonalityId + 1,
        generationNumber: state.generationNumber + 1,
      };
    }
    case 'failed':
      return { ...state, phase: action.resumeAt, error: action.message };
    case 'dismissError':
      return { ...state, error: undefined };
    case 'reset':
      return createInitialState();
  }
}
