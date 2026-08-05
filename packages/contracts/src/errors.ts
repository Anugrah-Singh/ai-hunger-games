import { z } from 'zod';

export const apiErrorSchema = z.strictObject({
  error: z.strictObject({
    code: z.string().min(1),
    message: z.string().min(1),
    requestId: z.string().min(1),
    details: z.unknown().optional(),
  }),
});

export type ApiErrorResponse = z.infer<typeof apiErrorSchema>;
