import { describe, expect, it } from 'vitest';
import { createInitialState, gameReducer } from './game-reducer.js';

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

  it('detects tied elimination votes', () => {
    let state = createInitialState();
    state = gameReducer(state, {
      type: 'votesReceived',
      votes: [
        { voter: 1, votedFor: 2, reason: 'A' },
        { voter: 2, votedFor: 1, reason: 'B' },
        { voter: 3, votedFor: 2, reason: 'C' },
        { voter: 4, votedFor: 1, reason: 'D' },
        { voter: 5, votedFor: 6, reason: 'E' },
        { voter: 6, votedFor: 7, reason: 'F' },
        { voter: 7, votedFor: 8, reason: 'G' },
        { voter: 8, votedFor: 5, reason: 'H' },
      ],
    });
    state = gameReducer(state, { type: 'resolveVotes' });

    expect(state.phase).toBe('tieBreak');
    expect(state.tiedIds).toEqual([1, 2]);
  });

  it('eliminates the only highest-voted personality', () => {
    let state = createInitialState();
    state = gameReducer(state, {
      type: 'votesReceived',
      votes: state.personalities.map((personality) => ({
        voter: personality.id,
        votedFor: personality.id === 1 ? 2 : 1,
        reason: 'Choice',
      })),
    });
    state = gameReducer(state, { type: 'resolveVotes' });

    expect(state.phase).toBe('eliminated');
    expect(state.personalities.find((personality) => personality.id === 1)?.alive).toBe(false);
  });
});
