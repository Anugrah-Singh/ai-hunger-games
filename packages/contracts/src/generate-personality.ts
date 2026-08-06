import { z } from 'zod';

export const generatePersonalityRequestSchema = z.strictObject({
  eliminatedName: z.string().trim().min(1).max(80),
  remainingNames: z.array(z.string().trim().min(1).max(80)).min(1).max(7),
});

export const generatePersonalityResponseSchema = z.strictObject({
  personality: z.strictObject({
    name: z.string().trim().min(1).max(80),
    trait: z.string().trim().min(1).max(240),
  }),
});

export type GeneratePersonalityRequest = z.infer<typeof generatePersonalityRequestSchema>;
export type GeneratePersonalityResponse = z.infer<typeof generatePersonalityResponseSchema>;
