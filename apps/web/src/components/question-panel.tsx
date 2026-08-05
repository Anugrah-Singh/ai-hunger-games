import { Send } from 'lucide-react';

interface QuestionPanelProps {
  question: string;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
}

export function QuestionPanel({ question, onQuestionChange, onSubmit }: QuestionPanelProps) {
  return (
    <section className="control-panel fade-in-up mt-8 p-5 sm:p-8" aria-labelledby="question-heading">
      <div className="mb-4 flex items-center gap-3">
        <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
        <h2
          id="question-heading"
          className="text-lg font-bold tracking-wider text-amber-400 uppercase"
        >
          Gamemaker control
        </h2>
        <span className="h-px flex-1 bg-gradient-to-r from-amber-700/60 to-transparent" />
      </div>

      <label
        htmlFor="arena-question"
        className="mb-3 block text-xs font-semibold tracking-widest text-zinc-400 uppercase"
      >
        Deploy a challenge to the remaining tributes
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="arena-question"
          type="text"
          value={question}
          maxLength={2_000}
          autoComplete="off"
          onChange={(event) => onQuestionChange(event.currentTarget.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onSubmit();
          }}
          placeholder="Enter a question or scenario..."
          className="min-h-13 flex-1 rounded-md border border-amber-900/60 bg-zinc-950 px-4 py-3 text-sm text-white placeholder:text-zinc-500 transition-all focus:border-amber-500 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 focus:outline-none"
        />
        <button
          type="button"
          onClick={onSubmit}
          disabled={!question.trim()}
          className="flex min-h-13 items-center justify-center gap-2 rounded-md border border-amber-400/80 bg-amber-600 px-6 py-3 text-sm font-bold tracking-wider text-white uppercase transition-all hover:bg-amber-500 hover:shadow-lg hover:shadow-amber-600/20 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 disabled:cursor-not-allowed disabled:border-zinc-800 disabled:bg-zinc-900 disabled:text-zinc-600"
        >
          <Send aria-hidden="true" size={17} />
          Deploy
        </button>
      </div>
    </section>
  );
}
