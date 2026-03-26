import { Body, Controller, Post } from '@nestjs/common';
import { ApiCreatedResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { SkipThrottle, Throttle } from '@nestjs/throttler';
import { ExtractDto, ExtractResponse } from '../../application/dtos/extract.dto';
import { ExtractDocumentsUseCase } from '../../application/use-cases/extract-documents.use-case';

@ApiTags('extract')
@Controller('extract')
@SkipThrottle({ ask: true, act: true })
@Throttle({ extract: {} })
export class ExtractController {
  constructor(
    private readonly extractDocuments: ExtractDocumentsUseCase,
  ) {}

  @Post()
  @ApiOperation({ summary: 'Surface Extract com schema de saida governado' })
  @ApiCreatedResponse({ description: 'Payload estruturado da surface Extract' })
  extract(@Body() dto: ExtractDto): Promise<ExtractResponse> {
    return this.extractDocuments.execute(dto);
  }
}
