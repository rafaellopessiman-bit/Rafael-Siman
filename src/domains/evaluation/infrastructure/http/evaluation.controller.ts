import {
  Body,
  Controller,
  Get,
  Inject,
  Param,
  Post,
  Query,
  HttpCode,
  HttpStatus,
  NotFoundException,
} from '@nestjs/common';
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { SkipThrottle } from '@nestjs/throttler';
import { Public } from '../../../../shared/guards/public.decorator';
import { RunEvalDto } from '../../application/dto/run-eval.dto';
import { RunEvalUseCase } from '../../application/use-cases/run-eval.use-case';
import { IEvalRunRepository, EVAL_RUN_REPOSITORY } from '../../domain/repositories/eval-run.repository.interface';
import { IEvalRun } from '../../domain/interfaces/eval-run.interface';
import { PaginationQueryDto, PaginatedResponseDto, paginate } from '../../../../shared/dto/pagination.dto';

@ApiTags('evaluation')
@Controller('eval')
@Public()
@SkipThrottle({ ask: true, act: true, extract: true })
export class EvaluationController {
  constructor(
    private readonly runEvalUseCase: RunEvalUseCase,
    @Inject(EVAL_RUN_REPOSITORY)
    private readonly runRepo: IEvalRunRepository,
  ) {}

  @Post('run')
  @HttpCode(HttpStatus.CREATED)
  @ApiOperation({ summary: 'Executa um dataset de avaliação e persiste o resultado' })
  @ApiResponse({ status: HttpStatus.CREATED, description: 'Eval run criado com sucesso' })
  async runEval(@Body() dto: RunEvalDto): Promise<IEvalRun> {
    return this.runEvalUseCase.execute({
      datasetId: dto.datasetId,
      triggeredBy: dto.triggeredBy,
    });
  }

  @Get('runs')
  @ApiOperation({ summary: 'Lista os eval runs mais recentes (paginado)' })
  async findRecent(@Query() query: PaginationQueryDto): Promise<PaginatedResponseDto<IEvalRun>> {
    const [data, total] = await Promise.all([
      this.runRepo.findRecent(query.take, query.skip),
      this.runRepo.countRecent(),
    ]);
    return paginate(data, total, query);
  }

  @Get('runs/:id')
  @ApiOperation({ summary: 'Busca um eval run por ID' })
  @ApiResponse({ status: HttpStatus.OK, description: 'Eval run encontrado' })
  @ApiResponse({ status: HttpStatus.NOT_FOUND, description: 'Eval run não encontrado' })
  async findById(@Param('id') id: string): Promise<IEvalRun> {
    const run = await this.runRepo.findById(id);
    if (!run) {
      throw new NotFoundException(`EvalRun "${id}" not found`);
    }
    return run;
  }

  @Get('runs/dataset/:datasetId')
  @ApiOperation({ summary: 'Lista runs de um dataset específico (paginado)' })
  async findByDataset(
    @Param('datasetId') datasetId: string,
    @Query() query: PaginationQueryDto,
  ): Promise<PaginatedResponseDto<IEvalRun>> {
    const [data, total] = await Promise.all([
      this.runRepo.findByDataset(datasetId, query.take, query.skip),
      this.runRepo.countByDataset(datasetId),
    ]);
    return paginate(data, total, query);
  }
}
