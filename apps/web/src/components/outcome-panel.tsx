import { Crown, LoaderCircle, Skull, Sparkles, ArrowRight } from 'lucide-react';
import type { Personality } from '../types/game.js';

interface OutcomePanelProps {
  eliminated: Personality | undefined;
  replacement?: Personality | undefined;
  winner: Personality | undefined;
  isGeneratingReplacement: boolean;
  onNextRound: () => void;
}

export function OutcomePanel({
  eliminated,
  replacement,
  winner,
  isGeneratingReplacement,
  onNextRound,
}: OutcomePanelProps) {
  if (winner) {
    return (
      <section className="border border-amber-500/50 bg-gradient-to-br from-[#b45309] via-[#78350f_55%] to-[#271404] shadow-[0_0_50px_rgba(245,158,11,0.3)] rounded-xl animate-[fadeInUp_300ms_cubic-bezier(0,0,0.2,1)_both] mt-8 overflow-hidden p-8 text-center sm:p-12">
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
    <section className="border border-amber-700/50 bg-[radial-gradient(circle_at_top,rgba(146,64,14,0.35),rgba(9,9,11,0.98)_65%)] rounded-xl animate-[fadeInUp_300ms_cubic-bezier(0,0,0.2,1)_both] mt-8 p-8 text-center sm:p-12">
      <div className="flex flex-col items-center justify-center gap-8 md:flex-row md:items-stretch">
        {/* Eliminated Personality */}
        <div className="flex-1 rounded-xl bg-black/40 p-6 border border-red-500/30 relative overflow-hidden">
          <div className="absolute inset-0 bg-red-500/5" />
          <Skull aria-hidden="true" size={48} className="mx-auto text-red-500/80" />
          <p className="mt-4 text-[10px] font-bold tracking-[0.3em] text-red-500/80 uppercase">
            Eliminated
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-wide text-zinc-300 uppercase line-through decoration-red-500/50">
            {eliminated.name}
          </h2>
          <p className="mt-2 text-xs text-zinc-500 leading-relaxed max-w-xs mx-auto line-clamp-3">
            {eliminated.trait}
          </p>
        </div>

        {/* Arrow Divider */}
        <div className="flex items-center justify-center shrink-0">
          <div className="rounded-full bg-zinc-900 border border-zinc-800 p-3 shadow-xl">
            <ArrowRight size={24} className="text-zinc-500" />
          </div>
        </div>

        {/* Replacement Personality */}
        <div className="flex-1 rounded-xl bg-black/40 p-6 border border-amber-400/30 relative overflow-hidden min-h-[220px] flex flex-col justify-center">
          <div className="absolute inset-0 bg-amber-400/5" />
          {replacement ? (
            <div className="fade-in">
              <Sparkles aria-hidden="true" size={48} className="mx-auto text-amber-400" />
              <p className="mt-4 text-[10px] font-bold tracking-[0.3em] text-amber-400 uppercase">
                New Challenger
              </p>
              <h2 className="mt-2 text-2xl font-bold tracking-wide text-white uppercase shadow-amber-400">
                {replacement.name}
              </h2>
              <p className="mt-2 text-xs text-amber-100/80 leading-relaxed max-w-xs mx-auto line-clamp-3">
                {replacement.trait}
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-amber-500/70">
              <LoaderCircle className="animate-spin" size={32} />
              <span className="text-xs font-semibold tracking-widest uppercase mt-2">
                Summoning...
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="mt-10">
        {!replacement || isGeneratingReplacement ? (
          <div className="inline-flex items-center justify-center gap-3 rounded-md border border-zinc-800 bg-zinc-900/50 px-8 py-3.5 text-sm font-semibold text-zinc-400 opacity-70 cursor-not-allowed">
            <LoaderCircle className="animate-spin text-amber-500" size={18} />
            Awaiting new challenger...
          </div>
        ) : (
          <button
            type="button"
            onClick={onNextRound}
            className="inline-flex rounded-md border border-amber-400 bg-amber-600 px-10 py-4 text-sm font-bold tracking-wider text-white uppercase shadow-lg shadow-amber-600/20 transition-all hover:bg-amber-500 hover:scale-[1.02] active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
          >
            Enter The Arena
          </button>
        )}
      </div>
    </section>
  );
}
