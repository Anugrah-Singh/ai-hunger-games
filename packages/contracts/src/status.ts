import { z } from 'zod';

export const statusResponseSchema = z.strictObject({
  trackingEnabled: z.boolean(),
  requestsUsed: z.number().int().nonnegative(),
  requestLimit: z.number().int().positive(),
  remaining: z.number().int().nonnegative(),
  disabled: z.boolean(),
  percentageUsed: z.number().min(0),
});

export type StatusResponse = z.infer<typeof statusResponseSchema>;
