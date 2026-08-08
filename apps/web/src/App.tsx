import { AnswersPanel } from './components/answers-panel.js';
import { Arena } from './components/arena.js';
import { ErrorBanner } from './components/error-banner.js';
import { GameHeader } from './components/game-header.js';
import { OutcomePanel } from './components/outcome-panel.js';
import { QuestionPanel } from './components/question-panel.js';
import { RoundCompletePanel } from './components/round-complete-panel.js';
import { VotingPanel } from './components/voting-panel.js';
import { useElapsedSeconds } from './hooks/use-elapsed-seconds.js';
import { useGameEngine } from './hooks/useGameEngine.js';

export default function App() {
  const {
    state,
    dispatch,
    alive,
    busy,
    isGeneratingReplacement,
    askQuestion,
    beginVoting,
    reset,
  } = useGameEngine();

  const elapsedSeconds = useElapsedSeconds(busy);

  const eliminated = state.eliminatedId
    ? state.personalities.find((personality) => personality.id === state.eliminatedId)
    : undefined;
  const winner = state.phase === 'winner' ? alive[0] : undefined;

  return (
    <main className="relative min-h-screen overflow-hidden bg-zinc-950 px-4 py-6 text-zinc-100 sm:px-6 sm:py-10">
      <div className="pointer-events-none fixed inset-0 opacity-30 bg-[repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(255,255,255,0.02)_3px,rgba(255,255,255,0.02)_5px)] animate-[scanline-drift_0.5s_linear_infinite]" aria-hidden="true" />
      <div
        className="pointer-events-none fixed inset-x-0 top-0 mx-auto h-[42rem] max-w-5xl bg-[radial-gradient(circle_at_top,rgba(245,158,11,0.12),transparent_70%)] blur-[50px]"
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
            replacement={state.replacementPersonality}
            winner={winner}
            isGeneratingReplacement={isGeneratingReplacement}
            onNextRound={() => dispatch({ type: 'nextRound' })}
          />
        ) : null}
      </div>
    </main>
  );
}
