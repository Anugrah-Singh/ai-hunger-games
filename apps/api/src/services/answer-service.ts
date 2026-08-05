import type { Answer, PersonalityInput } from '@ai-hunger-games/contracts';
import type { LlmClient } from '../llm/types.js';
import { mapWithConcurrency } from '../utilities/concurrency.js';
import { normalizeAnswer } from '../utilities/text.js';

const FALLBACKS: Record<string, string> = {
  'The Philosopher':
    'This question reaches beneath the obvious answer. We should examine its assumptions before deciding what it truly means.',
  'The Pragmatist':
    'The useful answer is the one that works under real constraints. Start with the simplest action that creates a measurable result.',
  'The Optimist':
    'There is genuine opportunity here. A constructive response can turn the challenge into progress for everyone involved.',
  'The Skeptic':
    'The claim needs stronger evidence before we accept it. Test the assumptions and look for what could disprove the conclusion.',
  'The Empath':
    'The human impact matters as much as the logical answer. We should consider how each person affected might experience the outcome.',
  'The Rebel':
    'The conventional answer is not automatically the right one. Challenge the default and look for an approach others have ignored.',
  'The Analyst':
    'Break the question into measurable parts, compare the evidence, and choose the conclusion best supported by the data.',
  'The Visionary':
    'The strongest answer should account for where this could lead next. Think beyond the immediate constraint and design for possibility.',
};

function fallbackFor(personality: PersonalityInput): string {
  return (
    FALLBACKS[personality.name] ??
    `${personality.name} considers the question carefully and offers a perspective shaped by being ${personality.trait.toLowerCase()}.`
  );
}

export class AnswerService {
  public constructor(
    private readonly llm: LlmClient,
    private readonly concurrency: number,
  ) {}

  public async generate(question: string, personalities: PersonalityInput[]): Promise<Answer[]> {
    return mapWithConcurrency(personalities, this.concurrency, async (personality) => {
      try {
        const answer = normalizeAnswer(await this.llm.generateAnswer(question, personality));
        return {
          id: personality.id,
          answer: answer.length >= 15 ? answer : fallbackFor(personality),
        };
      } catch (error) {
        console.error('LLM answer generation failed', {
          personalityId: personality.id,
          personalityName: personality.name,
          provider: this.llm.provider,
          model: this.llm.model,
          error,
        });

        return {
          id: personality.id,
          answer: fallbackFor(personality),
        };
      }
    });
  }
}
