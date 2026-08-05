import { X } from 'lucide-react';

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      role="alert"
      className="fade-in-up mt-6 flex items-start justify-between gap-4 rounded-lg border border-red-500/50 bg-red-950/40 p-4 text-red-100 backdrop-blur-sm"
    >
      <div>
        <p className="text-xs font-bold tracking-wider text-red-400 uppercase">Arena transmission failed</p>
        <p className="mt-1 text-sm text-red-200/90 leading-relaxed">{message}</p>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="rounded p-1 text-red-300 hover:bg-red-900/40 hover:text-white focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 transition-all"
      >
        <X aria-hidden="true" size={18} />
      </button>
    </div>
  );
}
