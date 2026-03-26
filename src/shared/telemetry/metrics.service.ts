import { Injectable } from '@nestjs/common';
import { Counter, Histogram, Registry, collectDefaultMetrics } from 'prom-client';

@Injectable()
export class MetricsService {
  private readonly registry = new Registry();

  readonly httpRequestDuration = new Histogram({
    name: 'atlas_http_request_duration_ms',
    help: 'Latência das requisições HTTP em milissegundos',
    labelNames: ['method', 'route', 'status'] as const,
    buckets: [10, 50, 100, 250, 500, 1000, 2500, 5000],
    registers: [this.registry],
  });

  readonly knowledgeJobsTotal = new Counter({
    name: 'atlas_knowledge_queue_jobs_total',
    help: 'Total de jobs de indexação enfileirados',
    labelNames: ['driver'] as const,
    registers: [this.registry],
  });

  readonly knowledgeJobErrors = new Counter({
    name: 'atlas_knowledge_queue_job_errors_total',
    help: 'Total de jobs de indexação com falha',
    registers: [this.registry],
  });

  readonly cacheHits = new Counter({
    name: 'atlas_ask_cache_total',
    help: 'Total de cache lookups (hit vs miss)',
    labelNames: ['result'] as const,
    registers: [this.registry],
  });

  readonly uploadsTotal = new Counter({
    name: 'atlas_knowledge_uploads_total',
    help: 'Total de uploads de documentos',
    labelNames: ['status'] as const,
    registers: [this.registry],
  });

  readonly cleanupDeletedTotal = new Counter({
    name: 'atlas_cleanup_deleted_total',
    help: 'Total de documentos removidos por cleanup agendado',
    labelNames: ['collection'] as const,
    registers: [this.registry],
  });

  constructor() {
    collectDefaultMetrics({ register: this.registry });
  }

  async getMetrics(): Promise<string> {
    return this.registry.metrics();
  }

  getContentType(): string {
    return this.registry.contentType;
  }
}
