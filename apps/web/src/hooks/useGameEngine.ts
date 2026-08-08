import { useEffect, useReducer, useRef, useState } from 'react';
import { api, userMessageFor } from '../api/client.js';
import { pickTheme } from '../data/themes.js';
import { alivePersonalities, createInitialState, gameReducer } from '../state/game-reducer.js';

export function useGameEngine() {
  const [state, dispatch] = useReducer(gameReducer, undefined, createInitialState);
  const [isGeneratingReplacement, setIsGeneratingReplacement] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  const alive = alivePersonalities(state);
  const busy = state.phase === 'generatingAnswers' || state.phase === 'generatingVotes';

  const freshController = (): AbortController => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    return controller;
  };

  useEffect(
    () => () => {
      controllerRef.current?.abort();
    },
    [],
  );

  useEffect(() => {
    if (state.phase !== 'eliminated' || !state.eliminatedId) return;

    const eliminated = state.personalities.find((p) => p.id === state.eliminatedId);
    if (!eliminated) return;

    const remainingNames = state.personalities.filter((p) => p.alive).map((p) => p.name);

    setIsGeneratingReplacement(true);
    const controller = freshController();

    api
      .generatePersonality({ eliminatedName: eliminated.name, remainingNames }, controller.signal)
      .then((result) => {
        const usedAvatars = state.personalities.map((p) => p.theme.avatar);
        dispatch({
          type: 'personalityReplaced',
          personality: {
            id: state.nextPersonalityId,
            name: result.personality.name,
            trait: result.personality.trait,
            alive: true,
            theme: pickTheme(usedAvatars),
          },
        });
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        console.error('Personality generation failed', { error });
      })
      .finally(() => {
        setIsGeneratingReplacement(false);
      });
  }, [state.phase, state.eliminatedId]);

  const askQuestion = async (): Promise<void> => {
    const question = state.question.trim();
    if (!question || busy) return;

    dispatch({ type: 'answersRequested' });
    const controller = freshController();

    try {
      const allAnswers = [];
      for (const p of alive) {
        if (controller.signal.aborted) break;
        const result = await api.generateAnswers(
          { question, personalities: [{ id: p.id, name: p.name, trait: p.trait }] },
          controller.signal,
        );
        allAnswers.push(...result.responses);
        dispatch({ type: 'answersReceived', answers: [...allAnswers] });

        // Wait 3 seconds before next request to avoid Free Tier 15 RPM limit
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      dispatch({ type: 'failed', message: userMessageFor(error), resumeAt: 'input' });
    }
  };

  const beginVoting = async (): Promise<void> => {
    if (state.answers.length !== alive.length || busy) return;

    dispatch({ type: 'votesRequested' });
    const controller = freshController();

    try {
      const allVotes = [];
      for (const p of alive) {
        if (controller.signal.aborted) break;
        const result = await api.generateSingleVote(
          {
            question: state.question,
            voterId: p.id,
            voterPersonality: { id: p.id, name: p.name, trait: p.trait },
            responses: state.answers,
          },
          controller.signal,
        );
        allVotes.push(result.vote);
        dispatch({ type: 'votesReceived', votes: [...allVotes] });

        // Wait 3 seconds before next request to avoid Free Tier 15 RPM limit
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      dispatch({ type: 'failed', message: userMessageFor(error), resumeAt: 'reviewAnswers' });
    }
  };

  const reset = (): void => {
    controllerRef.current?.abort();
    dispatch({ type: 'reset' });
  };

  return {
    state,
    dispatch,
    alive,
    busy,
    isGeneratingReplacement,
    askQuestion,
    beginVoting,
    reset,
  };
}
