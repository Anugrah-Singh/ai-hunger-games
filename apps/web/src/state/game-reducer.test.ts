import { describe, expect, it } from 'vitest';
import { ROUNDS_PER_GENERATION, createInitialState, gameReducer } from './game-reducer.js';

describe('game reducer', () => {
  it('moves through answer and vote phases', () => {
    let state = createInitialState();
    state = gameReducer(state, { type: 'questionChanged', question: 'Why?' });
    state = gameReducer(state, { type: 'answersRequested' });
    expect(state.phase).toBe('generatingAnswers');

    state = gameReducer(state, {
      type: 'answersReceived',
      answers: state.personalities.map((personality) => ({
        id: personality.id,
        answer: `Answer ${personality.id}`,
      })),
    });
    expect(state.phase).toBe('reviewAnswers');
  });

  it('accumulates scores across rounds without elimination until round 8', () => {
    let state = createInitialState();
    expect(state.roundInGeneration).toBe(1);

    state = gameReducer(state, {
      type: 'votesReceived',
      votes: state.personalities.map((p) => ({
        voter: p.id,
        votedFor: 1, // Everyone votes for personality #1
        reason: 'Best answer',
      })),
    });
    state = gameReducer(state, { type: 'resolveVotes' });

    expect(state.phase).toBe('roundComplete');
    expect(state.cumulativeScores[1]).toBe(8);
    expect(state.personalities.every((p) => p.alive)).toBe(true);
  });

  it('detects tied elimination scores on round 8', () => {
    let state = createInitialState();
    state.roundInGeneration = ROUNDS_PER_GENERATION;

    // Personality 1 and 2 both get 0 votes (tied for lowest score)
    state = gameReducer(state, {
      type: 'votesReceived',
      votes: [
        { voter: 1, votedFor: 3, reason: 'A' },
        { voter: 2, votedFor: 4, reason: 'B' },
        { voter: 3, votedFor: 5, reason: 'C' },
        { voter: 4, votedFor: 6, reason: 'D' },
        { voter: 5, votedFor: 7, reason: 'E' },
        { voter: 6, votedFor: 8, reason: 'F' },
        { voter: 7, votedFor: 3, reason: 'G' },
        { voter: 8, votedFor: 4, reason: 'H' },
      ],
    });
    state = gameReducer(state, { type: 'resolveVotes' });

    expect(state.phase).toBe('tieBreak');
    expect(state.tiedIds).toEqual([1, 2]);
  });

  it('eliminates the lowest-scoring personality on round 8', () => {
    let state = createInitialState();
    state.roundInGeneration = ROUNDS_PER_GENERATION;

    // Everyone except #1 gets votes, #1 gets 0 votes
    state = gameReducer(state, {
      type: 'votesReceived',
      votes: [
        { voter: 1, votedFor: 2, reason: 'Superior answer' },
        { voter: 2, votedFor: 2, reason: 'Superior answer' },
        { voter: 3, votedFor: 3, reason: 'Superior answer' },
        { voter: 4, votedFor: 4, reason: 'Superior answer' },
        { voter: 5, votedFor: 5, reason: 'Superior answer' },
        { voter: 6, votedFor: 6, reason: 'Superior answer' },
        { voter: 7, votedFor: 7, reason: 'Superior answer' },
        { voter: 8, votedFor: 8, reason: 'Superior answer' },
      ],
    });
    state = gameReducer(state, { type: 'resolveVotes' });

    expect(state.phase).toBe('eliminated');
    expect(state.eliminatedId).toBe(1);
    expect(state.personalities.find((personality) => personality.id === 1)?.alive).toBe(false);
  });

  it('replaces the eliminated personality with a new personality', () => {
    let state = createInitialState();
    state.roundInGeneration = ROUNDS_PER_GENERATION;

    state = gameReducer(state, {
      type: 'votesReceived',
      votes: [
        { voter: 1, votedFor: 2, reason: 'Superior answer' },
        { voter: 2, votedFor: 2, reason: 'Superior answer' },
        { voter: 3, votedFor: 3, reason: 'Superior answer' },
        { voter: 4, votedFor: 4, reason: 'Superior answer' },
        { voter: 5, votedFor: 5, reason: 'Superior answer' },
        { voter: 6, votedFor: 6, reason: 'Superior answer' },
        { voter: 7, votedFor: 7, reason: 'Superior answer' },
        { voter: 8, votedFor: 8, reason: 'Superior answer' },
      ],
    });
    state = gameReducer(state, { type: 'resolveVotes' });
    expect(state.eliminatedId).toBe(1);

    state = gameReducer(state, {
      type: 'personalityReplaced',
      personality: {
        id: 9,
        name: 'The Synthesizer',
        trait: 'Integrates opposing viewpoints',
        alive: true,
        theme: {
          avatar: 'bg-violet-500',
          border: 'border-violet-400',
          text: 'text-violet-300',
          glow: 'shadow-violet-500/20',
        },
      },
    });

    expect(state.replacementPersonality?.name).toBe('The Synthesizer');
    // Generation number and personalities list shouldn't be updated yet
    expect(state.generationNumber).toBe(1);

    state = gameReducer(state, { type: 'nextRound' });

    expect(state.generationNumber).toBe(2);
    expect(state.personalities.find((p) => p.id === 9)?.name).toBe('The Synthesizer');
    expect(state.personalities.filter((p) => p.alive)).toHaveLength(8);
  });
});
