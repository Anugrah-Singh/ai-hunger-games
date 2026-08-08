import { LoaderCircle } from 'lucide-react';
import type { Answer } from '@ai-hunger-games/contracts';
import type { GamePhase, Personality } from '../types/game.js';

interface AnswersPanelProps {
  phase: GamePhase;
  question: string;
  answers: Answer[];
  personalities: Personality[];
  elapsedSeconds: number;
  onBeginVoting: () => void;
}

export function AnswersPanel({
  phase,
  question,
  answers,
  personalities,
  elapsedSeconds,
  onBeginVoting,
}: AnswersPanelProps) {
  const generating = phase === 'generatingAnswers';

  return (
    <section
      className="border border-zinc-800 bg-gradient-to-b from-zinc-900/95 to-zinc-950/98 shadow-[0_10px_30px_-10px_rgba(0,0,0,0.5)] rounded-lg animate-[fadeInUp_300ms_cubic-bezier(0,0,0.2,1)_both] mt-8 p-5 sm:p-8"
      aria-live="polite"
    >
      <PanelQuestion question={question} />

      <div className="space-y-4">
        {answers.map((answer) => {
          const personality = personalities.find((entry) => entry.id === answer.id);
          if (!personality) return null;
          return (
            <article
              key={answer.id}
              className={`rounded-r-xl border-l-4 border-y border-r border-zinc-800/60 bg-zinc-900/60 p-4 sm:p-5 ${personality.theme.border}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className={`font-bold tracking-wide uppercase ${personality.theme.text}`}>
                  {personality.name}
                </h3>
                <span className="text-xs font-semibold tracking-wider text-amber-400/90 uppercase">
                  Tribute {personality.id}
                </span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-zinc-200">{answer.answer}</p>
            </article>
          );
        })}
      </div>

      {generating ? (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-800/60 bg-amber-950/40 p-4 text-amber-300">
          <div className="flex items-center gap-3 font-semibold tracking-wide text-sm uppercase">
            <LoaderCircle aria-hidden="true" className="animate-spin text-amber-400" size={18} />
            Receiving transmissions
          </div>
          <span className="rounded border border-amber-700/80 bg-zinc-950 px-3 py-1 font-mono text-lg font-bold text-amber-400">
            {elapsedSeconds}s
          </span>
        </div>
      ) : (
        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={onBeginVoting}
            className="rounded-md border border-amber-400 bg-amber-600 px-8 py-3.5 text-sm font-bold tracking-wider text-white uppercase shadow-lg shadow-amber-600/20 transition-all hover:bg-amber-500 hover:scale-[1.01] focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
          >
            Begin elimination voting
          </button>
        </div>
      )}
    </section>
  );
}

function PanelQuestion({ question }: { question: string }) {
  return (
    <div className="mb-6 border-l-4 border-amber-500/80 pl-4">
      <div className="text-xs font-semibold tracking-[0.2em] text-amber-400 uppercase">
        Arena challenge
      </div>
      <h2 className="mt-1 text-lg font-bold text-amber-200 sm:text-xl">{question}</h2>
    </div>
  );
}
