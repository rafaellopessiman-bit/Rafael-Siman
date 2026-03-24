import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

/**
 * Contrato de embedding para o atlas_local.
 *
 * ┌────────────────────────┬─────────────────────────────────┐
 * │ Propriedade            │ Valor contratual                │
 * ├────────────────────────┼─────────────────────────────────┤
 * │ Modelo padrão          │ text-embedding-3-small          │
 * │ Dimensão               │ 1536                            │
 * │ Similaridade           │ cosine                          │
 * │ Índice Atlas Local     │ knowledge_documents_embedding_  │
 * │                        │ vs_idx (01-init-db.js)          │
 * └────────────────────────┴─────────────────────────────────┘
 *
 * API: compatível com o endpoint OpenAI /v1/embeddings.
 * Configure EMBEDDING_API_KEY + EMBEDDING_BASE_URL no .env.
 * Sem chave → vetor zero (busca vetorial desativada).
 *
 * IMPORTANTE: se EMBEDDING_DIMENSIONS mudar, o índice vetorial
 * em 01-init-db.js (numDimensions) DEVE ser recriado.
 */

export const EMBEDDING_SERVICE = Symbol('EMBEDDING_SERVICE');

export interface IEmbeddingService {
  readonly model: string;
  readonly dimensions: number;

  /** Gera embedding para um único texto. */
  embed(text: string): Promise<number[]>;

  /** Gera embeddings em batch (única chamada de API). */
  embedBatch(texts: string[]): Promise<number[][]>;
}

interface EmbeddingApiResponse {
  data: Array<{ embedding: number[]; index: number }>;
}

@Injectable()
export class EmbeddingService implements IEmbeddingService {
  private readonly logger = new Logger(EmbeddingService.name);
  readonly model: string;
  readonly dimensions: number;
  private readonly apiKey: string | undefined;
  private readonly baseUrl: string;

  constructor(private readonly configService: ConfigService) {
    this.model = this.configService.get<string>(
      'EMBEDDING_MODEL',
      'text-embedding-3-small',
    );
    this.dimensions = this.configService.get<number>(
      'EMBEDDING_DIMENSIONS',
      1536,
    );
    this.apiKey = this.configService.get<string>('EMBEDDING_API_KEY');
    this.baseUrl = this.configService.get<string>(
      'EMBEDDING_BASE_URL',
      'https://api.openai.com/v1',
    );
  }

  get isConfigured(): boolean {
    return Boolean(this.apiKey && this.apiKey.trim().length > 0);
  }

  async embed(text: string): Promise<number[]> {
    if (!this.isConfigured) {
      this.logger.warn(
        'EMBEDDING_API_KEY não configurado — retornando vetor zero (busca vetorial desativada)',
      );
      return this.zeroVector();
    }

    const results = await this.callApi([text]);
    return results[0] ?? this.zeroVector();
  }

  async embedBatch(texts: string[]): Promise<number[][]> {
    if (!this.isConfigured) {
      return texts.map(() => this.zeroVector());
    }
    return this.callApi(texts);
  }

  private async callApi(inputs: string[]): Promise<number[][]> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}/embeddings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({ model: this.model, input: inputs }),
      });
    } catch (err) {
      this.logger.error('Falha na conexão com a API de embeddings', err);
      return inputs.map(() => this.zeroVector());
    }

    if (!response.ok) {
      const body = await response.text();
      this.logger.error(
        `Embedding API error ${response.status}: ${body}`,
      );
      return inputs.map(() => this.zeroVector());
    }

    const data = (await response.json()) as EmbeddingApiResponse;
    // A API retorna na ordem correta, mas ordenamos por index por segurança.
    const sorted = [...data.data].sort((a, b) => a.index - b.index);

    return sorted.map((item) => {
      if (item.embedding.length !== this.dimensions) {
        this.logger.warn(
          `Dimensão recebida (${item.embedding.length}) != esperada (${this.dimensions})`,
        );
        return this.zeroVector();
      }
      return item.embedding;
    });
  }

  private zeroVector(): number[] {
    return new Array<number>(this.dimensions).fill(0);
  }
}
