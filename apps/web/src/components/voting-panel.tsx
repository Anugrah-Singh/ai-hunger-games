import { LoaderCircle } from 'lucide-react';
import type { Vote } from '@ai-hunger-games/contracts';
import type { GamePhase, Personality } from '../types/game.js';
import { ROUNDS_PER_GENERATION, voteCount } from '../state/game-reducer.js';

interface VotingPanelProps {
  phase: GamePhase;
  votes: Vote[];
  personalities: Personality[];
  tiedIds: number[];
  elapsedSeconds: number;
  roundInGeneration: number;
  onResolve: () => void;
  onBreakTie: (id: number) => void;
}

export function VotingPanel({
  phase,
  votes,
  personalities,
  tiedIds,
  elapsedSeconds,
  roundInGeneration,
  onResolve,
  onBreakTie,
}: VotingPanelProps) {
  const generating = phase === 'generatingVotes';

  return (
    <section
      className="border border-amber-900/40 bg-gradient-to-br from-[#231208]/75 to-zinc-950/98 rounded-lg animate-[fadeInUp_300ms_cubic-bezier(0,0,0.2,1)_both] mt-8 p-5 sm:p-8"
      aria-live="polite"
    >
      <div className="mb-6 text-center">
        <h2 className="inline-block rounded-md border border-amber-700/60 bg-zinc-950 px-6 py-2 text-lg font-bold tracking-widest text-amber-400 uppercase">
          Best answer votes
        </h2>
      </div>

      <div className="space-y-4">
        {votes.map((vote) => {
          const voter = personalities.find((personality) => personality.id === vote.voter);
          const target = personalities.find((personality) => personality.id === vote.votedFor);
          if (!voter || !target) return null;

          return (
            <article
              key={vote.voter}
              className="rounded-r-xl border-l-4 border-emerald-600/80 border-y border-r border-zinc-800/60 bg-zinc-900/60 p-4"
            >
              <p className="font-semibold text-sm">
                <span className={voter.theme.text}>{voter.name}</span>
                <span className="px-2 text-zinc-500">→</span>
                <span className="font-bold text-emerald-400">Best answer: {target.name}</span>
              </p>
              <p className="mt-2 border-l-2 border-zinc-700/80 pl-3 text-xs leading-relaxed text-zinc-300 italic">
                “{vote.reason}”
              </p>
            </article>
          );
        })}
      </div>

      {generating ? (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-800/60 bg-amber-950/40 p-4 text-amber-300">
          <div className="flex items-center gap-3 font-semibold text-sm tracking-wide uppercase">
            <LoaderCircle aria-hidden="true" className="animate-spin text-amber-400" size={18} />
            Collecting anonymous votes
          </div>
          <span className="rounded border border-amber-700/80 bg-zinc-950 px-3 py-1 font-mono text-lg font-bold text-amber-400">
            {elapsedSeconds}s
          </span>
        </div>
      ) : null}

      {phase === 'reviewVotes' ? (
        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={onResolve}
            className="rounded-md border border-amber-400 bg-amber-600 px-8 py-3.5 text-sm font-bold tracking-wider text-white uppercase shadow-lg shadow-amber-600/20 transition-all hover:bg-amber-500 hover:scale-[1.01] focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
          >
            {roundInGeneration >= ROUNDS_PER_GENERATION
              ? 'Reveal final scores & eliminate lowest'
              : `Lock in round ${roundInGeneration} scores`}
          </button>
        </div>
      ) : null}

      {phase === 'tieBreak' ? (
        <div className="mt-8 rounded-xl border border-red-500/40 bg-red-950/20 p-6 backdrop-blur-sm">
          <h3 className="text-center text-lg font-bold tracking-wider text-red-300 uppercase">
            Tied vote — select tribute to eliminate
          </h3>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {tiedIds.map((id) => {
              const personality = personalities.find((entry) => entry.id === id);
              if (!personality) return null;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onBreakTie(id)}
                  className={`rounded-lg border bg-zinc-950/80 p-5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-red-500/80 hover:shadow-lg hover:shadow-red-500/10 focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 ${personality.theme.border}`}
                >
                  <span className={`text-base font-bold uppercase ${personality.theme.text}`}>
                    {personality.name}
                  </span>
                  <span className="mt-1.5 block text-xs text-zinc-400 leading-relaxed">
                    {personality.trait}
                  </span>
                  <span className="mt-3 block text-xs font-semibold text-red-400">
                    {voteCount(votes, id)} votes (Tied)
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
