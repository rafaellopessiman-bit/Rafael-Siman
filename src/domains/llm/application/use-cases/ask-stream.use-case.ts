import { Injectable, Inject, Logger } from '@nestjs/common';
import { Observable, Subscriber } from 'rxjs';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../../knowledge/domain/repositories/knowledge.repository.interface';
import {
  EMBEDDING_SERVICE,
  IEmbeddingService,
} from '../../../knowledge/domain/services/embedding.service';
import { GroqClientService, GroqStreamChunk } from '../../infrastructure/groq/groq-client.service';
import { ConfigService } from '@nestjs/config';

export interface AskStreamEvent {
  type: 'token' | 'sources' | 'done' | 'error';
  data: string;
}

const SYSTEM_PROMPT = `Você é um assistente especializado em análise de documentos.
Responda APENAS com base no contexto fornecido entre as tags <context>.
Se a resposta não puder ser encontrada no contexto, diga explicitamente que não encontrou informação suficiente.
Responda em português. Seja conciso e preciso.`;

@Injectable()
export class AskStreamUseCase {
  private readonly logger = new Logger(AskStreamUseCase.name);
  private readonly vectorSearchEnabled: boolean;

  constructor(
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
    @Inject(EMBEDDING_SERVICE)
    private readonly embeddingService: IEmbeddingService,
    private readonly groqClient: GroqClientService,
    private readonly configService: ConfigService,
  ) {
    this.vectorSearchEnabled =
      this.configService.get<string>('ATLAS_VECTOR_SEARCH_ENABLED', 'false') === 'true';
  }

  execute(query: string, topK = 5): Observable<MessageEvent> {
    return new Observable<MessageEvent>((subscriber) => {
      this.streamResponse(query, topK, subscriber).catch((err) => {
        this.logger.error('Stream error', err);
        subscriber.next(this.toMessageEvent({ type: 'error', data: 'Erro interno no stream' }));
        subscriber.complete();
      });
    });
  }

  private async streamResponse(
    query: string,
    topK: number,
    subscriber: Subscriber<MessageEvent>,
  ): Promise<void> {
    // 1. Retrieve context
    let chunks: { content: string; sourceFile?: string }[];

    if (this.vectorSearchEnabled) {
      const embedding = await this.embeddingService.embed(query);
      chunks = await this.knowledgeRepository.vectorSearch(embedding, topK);
    } else {
      chunks = await this.knowledgeRepository.searchText(query, topK);
    }

    const contextText = chunks
      .map((c, i) => `[${i + 1}] ${c.content}`)
      .join('\n\n');

    const sources = [
      ...new Set(
        chunks
          .map((c) => c.sourceFile)
          .filter((s): s is string => Boolean(s)),
      ),
    ];

    // 2. Emit sources first
    subscriber.next(
      this.toMessageEvent({ type: 'sources', data: JSON.stringify(sources) }),
    );

    // 3. Stream tokens from Groq
    const stream: AsyncGenerator<GroqStreamChunk> = this.groqClient.chatCompletionStream([
      { role: 'system', content: SYSTEM_PROMPT },
      {
        role: 'user',
        content: `<context>\n${contextText || 'Nenhum documento encontrado.'}\n</context>\n\nPergunta: ${query}`,
      },
    ]);

    for await (const chunk of stream) {
      if (chunk.done) {
        subscriber.next(this.toMessageEvent({ type: 'done', data: '' }));
        break;
      }
      if (chunk.token) {
        subscriber.next(this.toMessageEvent({ type: 'token', data: chunk.token }));
      }
    }

    subscriber.complete();
  }

  private toMessageEvent(event: AskStreamEvent): MessageEvent {
    return { data: JSON.stringify(event), type: event.type } as MessageEvent;
  }
}
