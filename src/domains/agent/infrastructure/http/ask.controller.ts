import { Body, Controller, Post, Query, Sse } from '@nestjs/common';
import { ApiCreatedResponse, ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { SkipThrottle, Throttle } from '@nestjs/throttler';
import { Observable } from 'rxjs';
import { AskDocumentsUseCase } from '../../../llm/application/use-cases/ask-documents.use-case';
import { AskStreamUseCase } from '../../../llm/application/use-cases/ask-stream.use-case';
import { AskDto, AskResponse, CitationMode } from '../../application/dtos/ask.dto';

@ApiTags('ask')
@Controller('ask')
@SkipThrottle({ act: true, extract: true })
@Throttle({ ask: {} })
export class AskController {
  constructor(
    private readonly askDocuments: AskDocumentsUseCase,
    private readonly askStream: AskStreamUseCase,
  ) {}

  @Post()
  @ApiOperation({ summary: 'Surface Ask com grounding e citacoes' })
  @ApiCreatedResponse({ description: 'Resposta grounded da surface Ask' })
  async ask(@Body() dto: AskDto): Promise<AskResponse> {
    const result = await this.askDocuments.execute({
      query: dto.query,
      topK: dto.topK,
    });
    const citationMode = dto.citationMode ?? CitationMode.SOURCES;
    const citations =
      citationMode === CitationMode.NONE
        ? []
        : result.sources.map((sourceFile, index) => ({
            index: index + 1,
            sourceFile,
          }));

    const answer =
      citationMode === CitationMode.INLINE && citations.length > 0
        ? `${result.answer}\n\nFontes:\n${citations
            .map((citation) => `[${citation.index}] ${citation.sourceFile}`)
            .join('\n')}`
        : result.answer;

    return {
      answer,
      citations,
      grounded: result.sources.length > 0,
      cached: result.cached,
      tokensUsed: result.tokensUsed,
      latencyMs: result.latencyMs,
    };
  }

  @Sse('stream')
  @ApiOperation({ summary: 'Surface Ask com streaming SSE em tempo real' })
  @ApiOkResponse({ description: 'Stream de tokens via Server-Sent Events' })
  stream(
    @Query('query') query: string,
    @Query('topK') topK?: string,
  ): Observable<MessageEvent> {
    const k = topK ? Math.min(Math.max(parseInt(topK, 10) || 5, 1), 20) : 5;
    return this.askStream.execute(query, k);
  }
}
