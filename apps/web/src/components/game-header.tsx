import { RotateCcw, Skull } from 'lucide-react';
import { ROUNDS_PER_GENERATION } from '../state/game-reducer.js';

interface GameHeaderProps {
  generationNumber: number;
  roundInGeneration: number;
  onReset: () => void;
}

export function GameHeader({ generationNumber, roundInGeneration, onReset }: GameHeaderProps) {
  return (
    <header className="border-b border-amber-600/30 pb-8 text-center">
      <div className="mb-3 flex items-center justify-center gap-3 text-amber-500">
        <span className="h-px w-20 bg-gradient-to-r from-transparent to-amber-500/60" />
        <Skull aria-hidden="true" size={24} className="text-amber-500" />
        <span className="h-px w-20 bg-gradient-to-l from-transparent to-amber-500/60" />
      </div>

      <p className="mb-2 text-xs font-semibold tracking-[0.35em] text-amber-500 uppercase">
        Capitol evolutionary simulation
      </p>
      <h1 className="arena-title text-4xl font-bold tracking-wider uppercase sm:text-6xl lg:text-7xl">
        AI Hunger Games
      </h1>
      <p className="mt-2 text-sm font-medium tracking-[0.2em] text-amber-200/90 sm:text-base">
        May the best algorithm survive and evolve
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
        <Stat label="Generation" value={`Gen #${generationNumber}`} />
        <Stat label="Gen round" value={`${roundInGeneration} / ${ROUNDS_PER_GENERATION}`} />
        <button
          type="button"
          onClick={onReset}
          className="flex h-14 items-center gap-2 rounded-md border border-amber-500/60 bg-amber-950/50 px-5 text-sm font-semibold tracking-wider text-amber-300 uppercase transition-all duration-200 hover:border-amber-400 hover:bg-amber-900/60 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
        >
          <RotateCcw aria-hidden="true" size={16} />
          Reset simulation
        </button>
      </div>
    </header>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex h-14 min-w-36 flex-col justify-center rounded-md border border-amber-800/60 bg-zinc-900/80 px-5 py-2 backdrop-blur-sm">
      <div className="text-[0.7rem] font-semibold tracking-widest text-amber-500/90 uppercase">
        {label}
      </div>
      <div className="mt-0.5 text-xl font-bold text-white">{value}</div>
    </div>
  );
}
