import { useEffect, useReducer, useRef, useState } from 'react';
import { api, userMessageFor } from './api/client.js';
import { AnswersPanel } from './components/answers-panel.js';
import { Arena } from './components/arena.js';
import { ErrorBanner } from './components/error-banner.js';
import { GameHeader } from './components/game-header.js';
import { OutcomePanel } from './components/outcome-panel.js';
import { QuestionPanel } from './components/question-panel.js';
import { RoundCompletePanel } from './components/round-complete-panel.js';
import { VotingPanel } from './components/voting-panel.js';
import { pickTheme } from './data/themes.js';
import { useElapsedSeconds } from './hooks/use-elapsed-seconds.js';
import { alivePersonalities, createInitialState, gameReducer } from './state/game-reducer.js';

export default function App() {
  const [state, dispatch] = useReducer(gameReducer, undefined, createInitialState);
  const [isGeneratingReplacement, setIsGeneratingReplacement] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const alive = alivePersonalities(state);
  const busy = state.phase === 'generatingAnswers' || state.phase === 'generatingVotes';
  const elapsedSeconds = useElapsedSeconds(busy);

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

    const remainingNames = state.personalities
      .filter((p) => p.alive)
      .map((p) => p.name);

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

  const freshController = (): AbortController => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    return controller;
  };

  const askQuestion = async (): Promise<void> => {
    const question = state.question.trim();
    if (!question || busy) return;

    dispatch({ type: 'answersRequested' });
    const controller = freshController();

    try {
      const result = await api.generateAnswers(
        {
          question,
          personalities: alive.map(({ id, name, trait }) => ({ id, name, trait })),
        },
        controller.signal,
      );
      dispatch({ type: 'answersReceived', answers: result.responses });
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
      const result = await api.generateVotes(
        { question: state.question, responses: state.answers },
        controller.signal,
      );
      dispatch({ type: 'votesReceived', votes: result.votes });
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      dispatch({ type: 'failed', message: userMessageFor(error), resumeAt: 'reviewAnswers' });
    }
  };

  const reset = (): void => {
    controllerRef.current?.abort();
    dispatch({ type: 'reset' });
  };

  const eliminated = state.eliminatedId
    ? state.personalities.find((personality) => personality.id === state.eliminatedId)
    : undefined;
  const winner = state.phase === 'winner' ? alive[0] : undefined;

  return (
    <main className="relative min-h-screen overflow-hidden bg-zinc-950 px-4 py-6 text-zinc-100 sm:px-6 sm:py-10">
      <div className="scanlines pointer-events-none fixed inset-0 opacity-30" aria-hidden="true" />
      <div
        className="spotlight pointer-events-none fixed inset-x-0 top-0 mx-auto h-[42rem] max-w-5xl"
        aria-hidden="true"
      />

      <div className="relative z-10 mx-auto max-w-7xl">
        <GameHeader
          generationNumber={state.generationNumber}
          roundInGeneration={state.roundInGeneration}
          onReset={reset}
        />
        {state.error ? (
          <ErrorBanner message={state.error} onDismiss={() => dispatch({ type: 'dismissError' })} />
        ) : null}

        <Arena
          personalities={state.personalities}
          votes={state.votes}
          cumulativeScores={state.cumulativeScores}
        />

        {state.phase === 'input' && alive.length > 1 ? (
          <QuestionPanel
            question={state.question}
            onQuestionChange={(question) => dispatch({ type: 'questionChanged', question })}
            onSubmit={() => void askQuestion()}
          />
        ) : null}

        {state.phase === 'generatingAnswers' || state.phase === 'reviewAnswers' ? (
          <AnswersPanel
            phase={state.phase}
            question={state.question}
            answers={state.answers}
            personalities={state.personalities}
            elapsedSeconds={elapsedSeconds}
            onBeginVoting={() => void beginVoting()}
          />
        ) : null}

        {['generatingVotes', 'reviewVotes', 'tieBreak'].includes(state.phase) ? (
          <VotingPanel
            phase={state.phase}
            votes={state.votes}
            personalities={state.personalities}
            tiedIds={state.tiedIds}
            elapsedSeconds={elapsedSeconds}
            roundInGeneration={state.roundInGeneration}
            onResolve={() => dispatch({ type: 'resolveVotes' })}
            onBreakTie={(id) => dispatch({ type: 'breakTie', id })}
          />
        ) : null}

        {state.phase === 'roundComplete' ? (
          <RoundCompletePanel
            roundInGeneration={state.roundInGeneration}
            cumulativeScores={state.cumulativeScores}
            personalities={state.personalities}
            onContinue={() => dispatch({ type: 'nextRound' })}
          />
        ) : null}

        {state.phase === 'eliminated' || state.phase === 'winner' ? (
          <OutcomePanel
            eliminated={state.phase === 'eliminated' ? eliminated : undefined}
            winner={winner}
            isGeneratingReplacement={isGeneratingReplacement}
            onNextRound={() => dispatch({ type: 'nextRound' })}
          />
        ) : null}
      </div>
    </main>
  );
}
