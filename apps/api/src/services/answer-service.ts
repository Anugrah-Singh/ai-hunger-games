import type { Answer, PersonalityInput } from '@ai-hunger-games/contracts';
import type { LlmClient } from '../llm/types.js';
import { normalizeAnswer } from '../utilities/text.js';

export class AnswerService {
  public constructor(
    private readonly llm: LlmClient,
    private readonly concurrency: number,
  ) {}

  public async generate(question: string, personalities: PersonalityInput[]): Promise<Answer[]> {
    if (personalities.length === 0) return [];

    const batchedAnswers = await this.llm.generateAnswers({
      question,
      personalities,
    });

    const answerMap = new Map<number, string>();
    for (const ba of batchedAnswers) {
      answerMap.set(ba.id, ba.answer);
    }

    return personalities.map((personality) => {
      const generated = answerMap.get(personality.id) || 'I have no answer.';
      const answer = normalizeAnswer(generated);

      return {
        id: personality.id,
        answer,
      };
    });
  }
}
