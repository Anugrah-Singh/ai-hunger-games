import { Crown, LoaderCircle, Skull } from 'lucide-react';
import type { Personality } from '../types/game.js';

interface OutcomePanelProps {
  eliminated: Personality | undefined;
  winner: Personality | undefined;
  isGeneratingReplacement: boolean;
  onNextRound: () => void;
}

export function OutcomePanel({
  eliminated,
  winner,
  isGeneratingReplacement,
  onNextRound,
}: OutcomePanelProps) {
  if (winner) {
    return (
      <section className="winner-panel fade-in-up mt-8 overflow-hidden rounded-2xl border border-amber-400/60 p-8 text-center sm:p-12">
        <Crown aria-hidden="true" size={72} className="mx-auto animate-pulse text-amber-200" />
        <p className="mt-4 text-xs font-semibold tracking-[0.35em] text-amber-200 uppercase">
          Sole survivor
        </p>
        <h2 className="mt-2 text-3xl font-bold tracking-wide text-white uppercase sm:text-5xl">
          {winner.name}
        </h2>
        <p className="mx-auto mt-4 max-w-xl rounded-lg border border-amber-400/30 bg-black/40 px-5 py-3 text-sm text-amber-100/90 leading-relaxed">
          {winner.trait}
        </p>
      </section>
    );
  }

  if (!eliminated) return null;

  return (
    <section className="elimination-panel fade-in-up mt-8 rounded-2xl border border-amber-700/60 p-8 text-center sm:p-12">
      <Skull aria-hidden="true" size={64} className="mx-auto animate-pulse text-amber-500" />
      <p className="mt-4 text-xs font-semibold tracking-[0.3em] text-amber-500 uppercase">
        Eliminated after 8 rounds
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-wide text-white uppercase sm:text-5xl">
        {eliminated.name}
      </h2>
      <p className="mt-2 text-sm text-zinc-400 leading-relaxed max-w-md mx-auto">{eliminated.trait}</p>

      {isGeneratingReplacement ? (
        <div className="mt-7 flex items-center justify-center gap-3 text-amber-300">
          <LoaderCircle className="animate-spin text-amber-400" size={20} />
          <span className="text-sm font-semibold">Generating replacement AI personality...</span>
        </div>
      ) : (
        <button
          type="button"
          onClick={onNextRound}
          className="mt-7 rounded-md border border-amber-400 bg-amber-600 px-8 py-3.5 text-sm font-bold tracking-wider text-white uppercase shadow-lg shadow-amber-600/20 transition-all hover:bg-amber-500 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
        >
          Begin Next Generation
        </button>
      )}
    </section>
  );
}
