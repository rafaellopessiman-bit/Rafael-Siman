import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Param,
  Query,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiParam } from '@nestjs/swagger';
import { IndexDocumentUseCase } from '../../application/use-cases/index-document.use-case';
import { SearchDocumentsUseCase } from '../../application/use-cases/search-documents.use-case';
import { DeleteDocumentUseCase } from '../../application/use-cases/delete-document.use-case';
import { FindBySourceFileUseCase } from '../../application/use-cases/find-by-source-file.use-case';
import { IndexDocumentDto } from '../../application/dtos/index-document.dto';
import { SearchQueryDto } from '../../application/dtos/search-query.dto';

@ApiTags('knowledge')
@Controller('knowledge')
export class KnowledgeController {
  constructor(
    private readonly indexDocumentUseCase: IndexDocumentUseCase,
    private readonly searchDocumentsUseCase: SearchDocumentsUseCase,
    private readonly deleteDocumentUseCase: DeleteDocumentUseCase,
    private readonly findBySourceFileUseCase: FindBySourceFileUseCase,
  ) {}

  @Get('search')
  @ApiOperation({ summary: 'Busca por texto nos documentos indexados' })
  search(@Query() dto: SearchQueryDto) {
    return this.searchDocumentsUseCase.execute(dto.q, dto.limit);
  }

  @Get(':sourceFile')
  @ApiOperation({ summary: 'Retorna chunks de um arquivo específico' })
  @ApiParam({ name: 'sourceFile', description: 'Caminho do arquivo de origem' })
  findBySource(@Param('sourceFile') sourceFile: string) {
    return this.findBySourceFileUseCase.execute(sourceFile);
  }

  @Post()
  @ApiOperation({ summary: 'Indexa um novo documento' })
  create(@Body() dto: IndexDocumentDto) {
    return this.indexDocumentUseCase.execute(dto);
  }

  @Delete(':sourceFile')
  @ApiOperation({ summary: 'Remove todos os chunks de um arquivo' })
  @ApiParam({ name: 'sourceFile', description: 'Caminho do arquivo de origem' })
  remove(@Param('sourceFile') sourceFile: string) {
    return this.deleteDocumentUseCase.execute(sourceFile);
  }
}
