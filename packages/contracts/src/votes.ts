import { z } from 'zod';
import {
  addUniqueIdValidation,
  answerSchema,
  personalitySchema,
  questionSchema,
  voteSchema,
} from './common.js';

export const votesRequestSchema = z.strictObject({
  question: questionSchema,
  responses: z.array(answerSchema).min(2).max(8).superRefine(addUniqueIdValidation),
});

export const votesResponseSchema = z.strictObject({
  votes: z.array(voteSchema).min(2).max(8),
});

export const singleVoteRequestSchema = z.strictObject({
  question: questionSchema,
  voterId: z.number().int().nonnegative(),
  voterPersonality: personalitySchema,
  responses: z.array(answerSchema).min(2).max(8).superRefine(addUniqueIdValidation),
});

export const singleVoteResponseSchema = z.strictObject({
  vote: voteSchema,
});

export type VotesRequest = z.infer<typeof votesRequestSchema>;
export type VotesResponse = z.infer<typeof votesResponseSchema>;
export type SingleVoteRequest = z.infer<typeof singleVoteRequestSchema>;
export type SingleVoteResponse = z.infer<typeof singleVoteResponseSchema>;
