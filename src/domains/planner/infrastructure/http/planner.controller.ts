import { Controller, Get, Put, Body, Query } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { Public } from '../../../../shared/guards/public.decorator';
import { UpsertDocumentIndexUseCase } from '../../application/use-cases/upsert-document-index.use-case';
import { UpsertIndexDto } from '../../application/dtos/upsert-index.dto';
import { DocumentStatus } from '@/domains/shared/enums';

@ApiTags('planner')
@Controller('planner')
@Public()
@SkipThrottle({ ask: true, act: true, extract: true })
export class PlannerController {
  constructor(
    private readonly upsertDocumentIndexUseCase: UpsertDocumentIndexUseCase,
  ) {}

  /**
   * Lista todos os documentos no índice.
   * Filtra por status quando fornecido: ?status=pending
   */
  @Get('index')
  @ApiOperation({ summary: 'Lista o índice de documentos (todos ou por status)' })
  @ApiQuery({ name: 'status', enum: DocumentStatus, required: false })
  async listIndex(@Query('status') status?: DocumentStatus) {
    const all = await this.upsertDocumentIndexUseCase.findAll();
    if (status) {
      return all.filter((doc) => doc.status === status);
    }
    return all;
  }

  /**
   * Lista documentos com status "pending" (ainda não indexados).
   */
  @Get('index/pending')
  @ApiOperation({ summary: 'Lista documentos pendentes de indexação' })
  findPending() {
    return this.upsertDocumentIndexUseCase.findPending();
  }

  /**
   * Upsert de entrada no índice de documentos.
   * Usado pelo pipeline de reindexação para registrar estado.
   */
  @Put('index')
  @ApiOperation({ summary: 'Cria ou atualiza entrada no índice de documentos' })
  upsert(@Body() dto: UpsertIndexDto) {
    return this.upsertDocumentIndexUseCase.execute(dto);
  }
}
