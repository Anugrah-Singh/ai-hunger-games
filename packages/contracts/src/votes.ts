import { z } from 'zod';
import { addUniqueIdValidation, answerSchema, questionSchema, voteSchema } from './common.js';

export const votesRequestSchema = z.strictObject({
  question: questionSchema,
  responses: z.array(answerSchema).min(2).max(8).superRefine(addUniqueIdValidation),
});

export const votesResponseSchema = z.strictObject({
  votes: z.array(voteSchema).min(2).max(8),
});

export type VotesRequest = z.infer<typeof votesRequestSchema>;
export type VotesResponse = z.infer<typeof votesResponseSchema>;
