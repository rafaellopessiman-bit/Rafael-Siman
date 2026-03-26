import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
  Logger,
} from '@nestjs/common';
import { Observable, finalize } from 'rxjs';
import { Request, Response } from 'express';
import { CORRELATION_ID_HEADER } from '../middleware/correlation-id.middleware';
import { MetricsService } from '../telemetry/metrics.service';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(LoggingInterceptor.name);

  constructor(private readonly metricsService?: MetricsService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const ctx = context.switchToHttp();
    const request = ctx.getRequest<Request>();
    const response = ctx.getResponse<Response>();
    const start = Date.now();
    const correlationId = request.headers[CORRELATION_ID_HEADER] as string | undefined;

    return next.handle().pipe(
      finalize(() => {
        const latencyMs = Date.now() - start;
        const route = request.route?.path ?? request.path ?? request.url;

        this.metricsService?.httpRequestDuration.observe(
          {
            method: request.method,
            route,
            status: String(response.statusCode),
          },
          latencyMs,
        );

        this.logger.log(
          JSON.stringify({
            method: request.method,
            url: request.url,
            status: response.statusCode,
            latencyMs,
            correlationId: correlationId ?? null,
          }),
        );
      }),
    );
  }
}
