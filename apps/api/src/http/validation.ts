import type { ZodType } from 'zod';

import { AppError } from '../errors/app-error.js';

export function parseBody<T>(schema: ZodType<T>, body: unknown): T {
  const result = schema.safeParse(body);

  if (result.success) {
    return result.data;
  }

  throw new AppError(
    400,
    'VALIDATION_ERROR',
    'The request body is invalid.',
    result.error.issues.map((issue) => ({
      path: issue.path.join('.'),
      message: issue.message,
    })),
  );
}
