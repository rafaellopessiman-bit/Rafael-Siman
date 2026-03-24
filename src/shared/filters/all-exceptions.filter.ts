import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

interface MongoServerError extends Error {
  code?: number;
}

interface MongooseValidationError extends Error {
  errors: Record<string, unknown>;
}

@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger(AllExceptionsFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let statusCode: number;
    let message: string | string[];

    if (exception instanceof HttpException) {
      statusCode = exception.getStatus();
      const exceptionResponse = exception.getResponse();
      if (typeof exceptionResponse === 'string') {
        message = exceptionResponse;
      } else {
        const resp = exceptionResponse as { message?: string | string[] };
        message = resp.message ?? exception.message;
      }
    } else if (this.isMongooseValidationError(exception)) {
      statusCode = HttpStatus.UNPROCESSABLE_ENTITY;
      message = Object.values(exception.errors)
        .map((e) => (e as { message?: string }).message ?? String(e))
        .join('; ');
    } else if (this.isMongoServerError(exception) && exception.code === 11000) {
      statusCode = HttpStatus.CONFLICT;
      message = 'Duplicate key';
    } else {
      statusCode = HttpStatus.INTERNAL_SERVER_ERROR;
      message = 'Internal server error';
    }

    this.logger.error(
      `${request.method} ${request.url} → ${statusCode}`,
      exception instanceof Error ? exception.stack : undefined,
    );

    response.status(statusCode).json({
      statusCode,
      message,
      timestamp: new Date().toISOString(),
      path: request.url,
    });
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
