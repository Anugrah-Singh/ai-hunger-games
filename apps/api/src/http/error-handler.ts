import type { FastifyInstance } from 'fastify';

import { isAppError } from '../errors/app-error.js';

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null;
}

function getStringProperty(value: unknown, property: string): string | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const propertyValue = value[property];

  return typeof propertyValue === 'string' ? propertyValue : undefined;
}

function getNumberProperty(value: unknown, property: string): number | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const propertyValue = value[property];

  return typeof propertyValue === 'number' ? propertyValue : undefined;
}

function hasProperty(value: unknown, property: string): boolean {
  return isRecord(value) && property in value;
}

function getErrorMessage(error: unknown): string | undefined {
  if (error instanceof Error && error.message.length > 0) {
    return error.message;
  }

  return getStringProperty(error, 'message');
}

export function registerErrorHandling(app: FastifyInstance): void {
  app.setNotFoundHandler((request, reply) =>
    reply.code(404).send({
      error: {
        code: 'NOT_FOUND',
        message: 'The requested API route does not exist.',
        requestId: request.id,
      },
    }),
  );

  app.setErrorHandler((error: unknown, request, reply) => {
    if (isAppError(error)) {
      return reply.code(error.statusCode).send({
        error: {
          code: error.code,
          message: error.message,
          requestId: request.id,
          ...(error.details === undefined
            ? {}
            : {
                details: error.details,
              }),
        },
      });
    }

    const errorCode = getStringProperty(error, 'code');

    if (errorCode === 'FST_ERR_CTP_INVALID_JSON_BODY') {
      return reply.code(400).send({
        error: {
          code: 'INVALID_JSON',
          message: 'The request body must contain valid JSON.',
          requestId: request.id,
        },
      });
    }

    if (errorCode === 'FST_ERR_CTP_BODY_TOO_LARGE') {
      return reply.code(413).send({
        error: {
          code: 'PAYLOAD_TOO_LARGE',
          message: 'The request body exceeds the maximum allowed size.',
          requestId: request.id,
        },
      });
    }

    if (hasProperty(error, 'validation')) {
      return reply.code(400).send({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'The request is invalid.',
          requestId: request.id,
        },
      });
    }

    const errorStatusCode = getNumberProperty(error, 'statusCode');

    const statusCode =
      errorStatusCode !== undefined && errorStatusCode >= 400 ? errorStatusCode : 500;

    if (statusCode >= 500) {
      request.log.error(
        {
          err: error,
        },
        'Unhandled request error',
      );
    }

    return reply.code(statusCode).send({
      error: {
        code: statusCode >= 500 ? 'INTERNAL_ERROR' : 'REQUEST_ERROR',
        message:
          statusCode >= 500
            ? 'An unexpected server error occurred.'
            : (getErrorMessage(error) ?? 'The request could not be completed.'),
        requestId: request.id,
      },
    });
  });
}
