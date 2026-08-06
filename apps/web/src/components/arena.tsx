import { Skull, Trophy } from 'lucide-react';
import type { Vote } from '@ai-hunger-games/contracts';
import type { Personality } from '../types/game.js';
import { cumulativeScore, voteCount } from '../state/game-reducer.js';

interface ArenaProps {
  personalities: Personality[];
  votes: Vote[];
  cumulativeScores: Record<number, number>;
}

function getInitials(name: string): string {
  const clean = name.replace(/^The\s+/, '');
  const words = clean.split(' ').filter(Boolean);
  const first = words[0]?.[0];
  const second = words[1]?.[0];
  if (first && second) {
    return `${first}${second}`.toUpperCase();
  }
  return clean.substring(0, 2).toUpperCase();
}

export function Arena({ personalities, votes, cumulativeScores }: ArenaProps) {
  return (
    <section className="arena-panel mt-8 p-5 sm:p-8" aria-labelledby="arena-heading">
      <div className="mb-6 text-center">
        <h2
          id="arena-heading"
          className="inline-block border-y border-amber-600/40 px-6 py-1.5 text-lg font-bold tracking-[0.2em] text-amber-400 uppercase"
        >
          The arena
        </h2>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 sm:gap-6">
        {personalities.map((personality) => {
          const totalPoints = cumulativeScore(cumulativeScores, personality.id);
          const roundVotes = voteCount(votes, personality.id);

          return (
            <article
              key={personality.id}
              aria-label={
                personality.alive ? personality.name : `${personality.name} — eliminated`
              }
              className={`relative flex flex-col items-center rounded-xl border p-4 transition-all duration-300 ${
                personality.alive
                  ? `border-zinc-800 bg-zinc-900/70 ${personality.theme.glow} shadow-md hover:-translate-y-1 hover:border-amber-500/40 hover:bg-zinc-900`
                  : 'border-zinc-900 bg-zinc-950/60 opacity-40 grayscale'
              }`}
            >
              <div className="absolute top-2.5 right-2.5 rounded border border-amber-900/60 bg-black/60 px-1.5 py-0.5 text-[0.65rem] font-semibold text-amber-400/90">
                T{personality.id}
              </div>

              <div className="mt-2 flex h-20 items-center justify-center">
                <div
                  className={`flex h-16 w-16 items-center justify-center rounded-xl border-2 transition-all duration-300 ${
                    personality.alive
                      ? `${personality.theme.border} bg-zinc-950/80 backdrop-blur-sm shadow-md`
                      : 'border-zinc-800 bg-zinc-950'
                  }`}
                >
                  {personality.alive ? (
                    <span className={`text-xl font-bold tracking-wider ${personality.theme.text}`}>
                      {getInitials(personality.name)}
                    </span>
                  ) : (
                    <Skull aria-hidden="true" size={24} className="text-zinc-600" />
                  )}
                </div>
              </div>

              <h3
                className={`mt-2 text-center text-xs font-bold tracking-wide uppercase ${
                  personality.alive ? personality.theme.text : 'text-zinc-500'
                }`}
              >
                {personality.name}
              </h3>

              <p className="mt-1 min-h-9 text-center text-[0.75rem] leading-relaxed text-zinc-400 line-clamp-2">
                {personality.trait}
              </p>

              {personality.alive ? (
                <div className="mt-3 flex w-full items-center justify-center gap-1.5 rounded border border-amber-800/60 bg-amber-950/50 py-1 text-center text-xs font-semibold text-amber-300">
                  <Trophy size={13} className="text-amber-400" />
                  <span>
                    {totalPoints} {totalPoints === 1 ? 'pt' : 'pts'}
                    {votes.length > 0 ? ` (+${roundVotes})` : ''}
                  </span>
                </div>
              ) : null}

            {!personality.alive ? (
              <div className="mt-3 w-full rounded border border-zinc-800 bg-zinc-950 py-1 text-center text-[0.65rem] font-semibold tracking-wider text-zinc-500 uppercase">
                Eliminated
              </div>
            ) : null}
          </article>
        );
      })}
      </div>
    </section>
  );
}
