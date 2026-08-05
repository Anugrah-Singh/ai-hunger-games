import { z } from 'zod';
import {
  addUniqueIdValidation,
  answerSchema,
  personalitySchema,
  questionSchema,
} from './common.js';

export const answersRequestSchema = z.strictObject({
  question: questionSchema,
  personalities: z.array(personalitySchema).min(2).max(8).superRefine(addUniqueIdValidation),
});

export const answersResponseSchema = z.strictObject({
  responses: z.array(answerSchema).min(2).max(8),
});

export type AnswersRequest = z.infer<typeof answersRequestSchema>;
export type AnswersResponse = z.infer<typeof answersResponseSchema>;
