const MAXIMUM_ANSWER_LENGTH = 1_500;
const MAXIMUM_REASON_LENGTH = 240;

const KNOWN_GENERATION_CORRECTIONS: ReadonlyArray<readonly [pattern: RegExp, replacement: string]> =
  [
    [/\bmis understand\b/giu, 'misunderstand'],
    [/\bmis understood\b/giu, 'misunderstood'],
    [/\bmis understanding\b/giu, 'misunderstanding'],
  ];

function normalizeWhitespace(text: string): string {
  return text.replace(/\s+/gu, ' ').trim();
}

function normalizePunctuationSpacing(text: string): string {
  let cleaned = text
    .replace(/\s+([,.;:!?])/gu, '$1')
    .replace(/,([^\s\d])/gu, ', $1')
    .replace(/;([^\s])/gu, '; $1')
    .replace(/:([^\s/])/gu, ': $1');

  // Strip markdown list markers and "Sentence 1:", "Sentence 2:" prefixes
  cleaned = cleaned.replace(/^\s*(?:[-*]|\d+\.)\s*/gmu, '');
  cleaned = cleaned.replace(/\*?\s*\*?Sentence \d+:\s*\*?\s*/gmu, '');

  return cleaned;
}

function applyKnownCorrections(text: string): string {
  return KNOWN_GENERATION_CORRECTIONS.reduce(
    (result, [pattern, replacement]) => result.replace(pattern, replacement),
    text,
  );
}

function normalizeGeneratedText(text: string): string {
  return applyKnownCorrections(normalizePunctuationSpacing(normalizeWhitespace(text)));
}

function extractSentences(text: string, maximumSentences: number): string {
  const segmenter = new Intl.Segmenter('en', {
    granularity: 'sentence',
  });

  const sentences = Array.from(segmenter.segment(text), ({ segment }) => segment.trim()).filter(
    Boolean,
  );

  return sentences.slice(0, maximumSentences).join(' ').trim();
}

export function normalizeAnswer(text: string, maximumSentences = 3): string {
  const normalized = normalizeGeneratedText(text);

  if (!normalized) {
    return '';
  }

  const limited = extractSentences(normalized, maximumSentences);

  return limited.slice(0, MAXIMUM_ANSWER_LENGTH).trim();
}

export function normalizeReason(text: string): string {
  const normalized = normalizeGeneratedText(text);

  if (!normalized) {
    return 'Their answer is the least aligned with my perspective.';
  }

  if (normalized.length <= MAXIMUM_REASON_LENGTH) {
    return normalized;
  }

  return `${normalized.slice(0, MAXIMUM_REASON_LENGTH - 3).trimEnd()}...`;
}
