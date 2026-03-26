import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Param,
  Query,
  HttpCode,
  HttpStatus,
  UseInterceptors,
  UploadedFile,
  ParseFilePipe,
  MaxFileSizeValidator,
  Inject,
  BadRequestException,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiTags, ApiOperation, ApiParam, ApiAcceptedResponse, ApiConsumes, ApiBody } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { extname } from 'path';

interface UploadedFile {
  originalname: string;
  mimetype: string;
  buffer: Buffer;
  size: number;
}
import { Public } from '../../../../shared/guards/public.decorator';
import { PaginationQueryDto, paginate, PaginatedResponseDto } from '../../../../shared/dto/pagination.dto';
import { IndexDocumentUseCase } from '../../application/use-cases/index-document.use-case';
import { SearchDocumentsUseCase } from '../../application/use-cases/search-documents.use-case';
import { DeleteDocumentUseCase } from '../../application/use-cases/delete-document.use-case';
import { FindBySourceFileUseCase } from '../../application/use-cases/find-by-source-file.use-case';
import { EnqueueKnowledgeIndexUseCase } from '../../application/use-cases/enqueue-knowledge-index.use-case';
import { IndexDocumentDto } from '../../application/dtos/index-document.dto';
import { SearchQueryDto } from '../../application/dtos/search-query.dto';
import {
  ALLOWED_EXTENSIONS,
  MAX_FILE_SIZE,
} from '../../application/dtos/upload-document.dto';
import { KNOWLEDGE_REPOSITORY, IKnowledgeRepository } from '../../domain/repositories/knowledge.repository.interface';
import { MetricsService } from '../../../../shared/telemetry/metrics.service';
import { FileType } from '../../../shared/enums';
import { KnowledgeDocumentDocument } from '../persistence/knowledge-document.schema';

@ApiTags('knowledge')
@Controller('knowledge')
@Public()
@SkipThrottle({ ask: true, act: true, extract: true })
export class KnowledgeController {
  constructor(
    private readonly indexDocumentUseCase: IndexDocumentUseCase,
    private readonly searchDocumentsUseCase: SearchDocumentsUseCase,
    private readonly deleteDocumentUseCase: DeleteDocumentUseCase,
    private readonly findBySourceFileUseCase: FindBySourceFileUseCase,
    private readonly enqueueKnowledgeIndex: EnqueueKnowledgeIndexUseCase,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepo: IKnowledgeRepository,
    private readonly metricsService: MetricsService,
  ) {}

  @Get()
  @ApiOperation({ summary: 'Lista documentos indexados (paginado)' })
  async listDocuments(
    @Query() pagination: PaginationQueryDto,
  ): Promise<PaginatedResponseDto<KnowledgeDocumentDocument>> {
    const [data, total] = await Promise.all([
      this.knowledgeRepo.findPaginated(pagination.skip, pagination.take),
      this.knowledgeRepo.countAll(),
    ]);
    return paginate(data, total, pagination);
  }

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
  @ApiOperation({ summary: 'Indexa um novo documento (síncrono)' })
  create(@Body() dto: IndexDocumentDto) {
    return this.indexDocumentUseCase.execute(dto);
  }

  @Post('upload')
  @HttpCode(HttpStatus.CREATED)
  @UseInterceptors(FileInterceptor('file'))
  @ApiConsumes('multipart/form-data')
  @ApiOperation({ summary: 'Upload de arquivo para indexação' })
  @ApiBody({
    schema: {
      type: 'object',
      properties: {
        file: { type: 'string', format: 'binary', description: 'Arquivo (.txt, .md, .json, .csv)' },
      },
    },
  })
  async upload(
    @UploadedFile(
      new ParseFilePipe({
        validators: [new MaxFileSizeValidator({ maxSize: MAX_FILE_SIZE })],
      }),
    )
    file: UploadedFile,
  ) {
    const ext = extname(file.originalname).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      throw new BadRequestException(
        `Extensão "${ext}" não permitida. Aceitas: ${[...ALLOWED_EXTENSIONS].join(', ')}`,
      );
    }

    const content = file.buffer.toString('utf-8');
    const fileType = ext as FileType;

    const result = await this.indexDocumentUseCase.execute({
      sourceFile: file.originalname,
      content,
      fileType,
    });

    this.metricsService.uploadsTotal.inc({ status: 'success' });

    return {
      sourceFile: file.originalname,
      fileType,
      sizeBytes: file.size,
      chunksCreated: Array.isArray(result) ? result.length : 1,
    };
  }

  @Post('async')
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({ summary: 'Enfileira indexação assíncrona de documento' })
  @ApiAcceptedResponse({ description: 'Indexação enfileirada com sucesso' })
  createAsync(@Body() dto: IndexDocumentDto) {
    return this.enqueueKnowledgeIndex.execute(dto);
  }

  @Delete(':sourceFile')
  @ApiOperation({ summary: 'Remove todos os chunks de um arquivo' })
  @ApiParam({ name: 'sourceFile', description: 'Caminho do arquivo de origem' })
  remove(@Param('sourceFile') sourceFile: string) {
    return this.deleteDocumentUseCase.execute(sourceFile);
  }
}
