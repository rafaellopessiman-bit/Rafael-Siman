import { Controller, Post, Get, Body, Param } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { Public } from '../../../../shared/guards/public.decorator';
import { AskDocumentsUseCase } from '../../application/use-cases/ask-documents.use-case';
import { GetCachedResponseUseCase } from '../../application/use-cases/get-cached-response.use-case';
import { AskQueryDto } from '../../application/dtos/ask-query.dto';

@ApiTags('llm')
@Controller('llm')
@Public()
@SkipThrottle({ ask: true, act: true, extract: true })
export class LlmController {
  constructor(
    private readonly askDocumentsUseCase: AskDocumentsUseCase,
    private readonly getCachedResponseUseCase: GetCachedResponseUseCase,
  ) {}

  /**
   * RAG endpoint — recebe pergunta, busca contexto nos documentos indexados,
   * chama Groq LLM e retorna resposta fundamentada nas fontes.
   */
  @Post('ask')
  @ApiOperation({ summary: 'Faz uma pergunta RAG sobre os documentos indexados' })
  ask(@Body() dto: AskQueryDto) {
    return this.askDocumentsUseCase.execute(dto);
  }

  /**
   * Consulta direta ao cache de respostas pelo hash da query.
   */
  @Get('cache/:hash')
  @ApiOperation({ summary: 'Consulta o cache de respostas LLM' })
  getCache(@Param('hash') hash: string) {
    return this.getCachedResponseUseCase.execute(hash);
  }
}
