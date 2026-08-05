import type { Answer, Vote } from '@ai-hunger-games/contracts';
import { INITIAL_PERSONALITIES } from '../data/personalities.js';
import type { GamePhase, GameState, Personality } from '../types/game.js';

export type GameAction =
  | { type: 'questionChanged'; question: string }
  | { type: 'answersRequested' }
  | { type: 'answersReceived'; answers: Answer[] }
  | { type: 'votesRequested' }
  | { type: 'votesReceived'; votes: Vote[] }
  | { type: 'resolveVotes' }
  | { type: 'breakTie'; id: number }
  | { type: 'nextRound' }
  | { type: 'failed'; message: string; resumeAt: GamePhase }
  | { type: 'dismissError' }
  | { type: 'reset' };

export function createInitialState(): GameState {
  return {
    phase: 'input',
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
    phase: remaining.length === 1 ? 'winner' : 'eliminated',
  };
}

function resolveVotes(state: GameState): GameState {
  const alive = alivePersonalities(state);
  if (state.votes.length !== alive.length) {
    return { ...state, error: 'A complete vote set is required before elimination.' };
  }

  const counts = new Map(alive.map((personality) => [personality.id, 0]));
  for (const vote of state.votes) {
    counts.set(vote.votedFor, (counts.get(vote.votedFor) ?? 0) + 1);
  }

  const maximum = Math.max(...counts.values());
  const tiedIds = [...counts.entries()].filter(([, count]) => count === maximum).map(([id]) => id);

  if (tiedIds.length > 1) return { ...state, tiedIds, phase: 'tieBreak' };
  const eliminatedId = tiedIds[0];
  return eliminatedId === undefined ? state : eliminate(state, eliminatedId);
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
        question: '',
        answers: [],
        votes: [],
        tiedIds: [],
        eliminatedId: undefined,
        error: undefined,
      };
    case 'failed':
      return { ...state, phase: action.resumeAt, error: action.message };
    case 'dismissError':
      return { ...state, error: undefined };
    case 'reset':
      return createInitialState();
  }
}
