import { ArrowRight, Trophy } from 'lucide-react';
import type { Personality } from '../types/game.js';
import { ROUNDS_PER_GENERATION, cumulativeScore } from '../state/game-reducer.js';

interface RoundCompletePanelProps {
  roundInGeneration: number;
  cumulativeScores: Record<number, number>;
  personalities: Personality[];
  onContinue: () => void;
}

export function RoundCompletePanel({
  roundInGeneration,
  cumulativeScores,
  personalities,
  onContinue,
}: RoundCompletePanelProps) {
  const alive = personalities.filter((p) => p.alive);
  const leaderboard = [...alive].sort(
    (a, b) => cumulativeScore(cumulativeScores, b.id) - cumulativeScore(cumulativeScores, a.id),
  );

  return (
    <section className="border border-zinc-800 bg-gradient-to-b from-zinc-900/95 to-zinc-950/98 shadow-[0_10px_30px_-10px_rgba(0,0,0,0.5)] rounded-lg animate-[fadeInUp_300ms_cubic-bezier(0,0,0.2,1)_both] mt-8 p-5 sm:p-8" aria-live="polite">
      <div className="mb-6 border-l-4 border-amber-500/80 pl-4">
        <div className="text-xs font-semibold tracking-[0.2em] text-amber-400 uppercase">
          Generation Standings — Round {roundInGeneration} of {ROUNDS_PER_GENERATION}
        </div>
        <h2 className="mt-1 text-lg font-bold text-amber-200 sm:text-xl">
          Cumulative Points Leaderboard
        </h2>
      </div>

      <div className="space-y-3">
        {leaderboard.map((personality, index) => {
          const score = cumulativeScore(cumulativeScores, personality.id);
          return (
            <article
              key={personality.id}
              className={`flex items-center justify-between rounded-lg border-l-4 border-y border-r border-zinc-800/60 bg-zinc-900/60 p-4 ${personality.theme.border}`}
            >
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-zinc-950 text-xs font-bold text-zinc-400">
                  #{index + 1}
                </span>
                <div>
                  <h3 className={`font-bold tracking-wide uppercase ${personality.theme.text}`}>
                    {personality.name}
                  </h3>
                  <p className="text-xs text-zinc-400">{personality.trait}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 rounded border border-amber-800/60 bg-amber-950/40 px-3 py-1.5 font-mono text-sm font-bold text-amber-300">
                <Trophy size={15} className="text-amber-400" />
                {score} {score === 1 ? 'pt' : 'pts'}
              </div>
            </article>
          );
        })}
      </div>

      <div className="mt-8 text-center">
        <button
          type="button"
          onClick={onContinue}
          className="inline-flex items-center gap-2 rounded-md border border-amber-400 bg-amber-600 px-8 py-3.5 text-sm font-bold tracking-wider text-white uppercase shadow-lg shadow-amber-600/20 transition-all hover:bg-amber-500 hover:scale-[1.01] focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
        >
          <span>Proceed to Round {roundInGeneration + 1}</span>
          <ArrowRight size={17} />
        </button>
      </div>
    </section>
  );
}
