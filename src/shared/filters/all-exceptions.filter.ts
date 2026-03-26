import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';
import { randomBytes } from 'crypto';

interface MongoServerError extends Error {
  code?: number;
}

interface MongooseValidationError extends Error {
  errors: Record<string, unknown>;
}

type ErrorCategory = 'validation' | 'conflict' | 'auth' | 'not_found' | 'internal';

@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger(AllExceptionsFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    const errorId = randomBytes(4).toString('hex');
    const correlationId =
      (request.headers['x-correlation-id'] as string) ?? errorId;

    let statusCode: number;
    let message: string | string[];
    let category: ErrorCategory;
    let details: Array<{ field?: string; issue: string }> | undefined;

    if (exception instanceof HttpException) {
      statusCode = exception.getStatus();
      const exceptionResponse = exception.getResponse();
      if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else {
        const resp = exceptionResponse as { message?: string | string[] };
        message = resp.message ?? exception.message;
      }

      // Extract validation details from class-validator pipe errors
      if (statusCode === HttpStatus.BAD_REQUEST && Array.isArray(message)) {
        details = message.map((m) => ({ issue: m }));
      }

      category = this.categorize(statusCode);
    } else if (this.isMongooseValidationError(exception)) {
      statusCode = HttpStatus.UNPROCESSABLE_ENTITY;
      const errors = Object.entries(exception.errors);
      details = errors.map(([field, e]) => ({
        field,
        issue: (e as { message?: string }).message ?? String(e),
      }));
      message = details.map((d) => d.issue).join('; ');
      category = 'validation';
    } else if (this.isMongoServerError(exception) && exception.code === 11000) {
      statusCode = HttpStatus.CONFLICT;
      message = 'Duplicate key';
      category = 'conflict';
    } else {
      statusCode = HttpStatus.INTERNAL_SERVER_ERROR;
      message = 'Internal server error';
      category = 'internal';
    }

    this.logger.error(
      `[${errorId}] ${request.method} ${request.url} → ${statusCode}`,
      exception instanceof Error ? exception.stack : undefined,
    );

    response.status(statusCode).json({
      statusCode,
      message,
      errorId,
      correlationId,
      category,
      retryable: statusCode >= 500,
      ...(details ? { details } : {}),
      timestamp: new Date().toISOString(),
      path: request.url,
    });
  }

  private categorize(status: number): ErrorCategory {
    if (status === HttpStatus.NOT_FOUND) return 'not_found';
    if (status === HttpStatus.CONFLICT) return 'conflict';
    if (status === HttpStatus.UNAUTHORIZED || status === HttpStatus.FORBIDDEN) return 'auth';
    if (status < 500) return 'validation';
    return 'internal';
  }

  private isMongoServerError(err: unknown): err is MongoServerError {
    return err instanceof Error && 'code' in err;
  }

  private isMongooseValidationError(err: unknown): err is MongooseValidationError {
    return (
      err instanceof Error &&
      err.constructor.name === 'ValidationError' &&
      'errors' in err &&
      typeof (err as MongooseValidationError).errors === 'object'
    );
  }
}
