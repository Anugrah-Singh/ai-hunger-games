import { z } from 'zod';

export const tributeIdSchema = z.number().int().positive().max(10_000);

export const questionSchema = z.string().trim().min(1).max(2_000);

export const personalitySchema = z.strictObject({
  id: tributeIdSchema,
  name: z.string().trim().min(1).max(80),
  trait: z.string().trim().min(1).max(240),
});

export const answerSchema = z.strictObject({
  id: tributeIdSchema,
  answer: z.string().trim().min(1).max(1_500),
});

export const voteSchema = z.strictObject({
  voter: tributeIdSchema,
  votedFor: tributeIdSchema,
  reason: z.string().trim().min(1).max(240),
});

export function addUniqueIdValidation<T extends { id: number }>(
  values: T[],
  context: z.RefinementCtx,
): void {
  const seen = new Set<number>();

  values.forEach((value, index) => {
    if (seen.has(value.id)) {
      context.addIssue({
        code: 'custom',
        path: [index, 'id'],
        message: 'IDs must be unique',
      });
    }
    seen.add(value.id);
  });
}

export type PersonalityInput = z.infer<typeof personalitySchema>;
export type Answer = z.infer<typeof answerSchema>;
export type Vote = z.infer<typeof voteSchema>;
