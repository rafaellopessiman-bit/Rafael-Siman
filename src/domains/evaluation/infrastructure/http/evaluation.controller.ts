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
import { ApiOperation, ApiQuery, ApiResponse, ApiTags } from '@nestjs/swagger';
import { Public } from '../../../../shared/guards/public.decorator';
import { RunEvalDto } from '../../application/dto/run-eval.dto';
import { RunEvalUseCase } from '../../application/use-cases/run-eval.use-case';
import { IEvalRunRepository, EVAL_RUN_REPOSITORY } from '../../domain/repositories/eval-run.repository.interface';
import { IEvalRun } from '../../domain/interfaces/eval-run.interface';

@ApiTags('evaluation')
@Controller('eval')
@Public()
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
  @ApiOperation({ summary: 'Lista os eval runs mais recentes' })
  @ApiQuery({ name: 'limit', required: false, type: Number, description: 'Máximo de resultados (default: 10)' })
  async findRecent(@Query('limit') limit?: string): Promise<IEvalRun[]> {
    const parsedLimit = limit ? parseInt(limit, 10) : 10;
    return this.runRepo.findRecent(parsedLimit);
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
  @ApiOperation({ summary: 'Lista runs de um dataset específico' })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  async findByDataset(
    @Param('datasetId') datasetId: string,
    @Query('limit') limit?: string,
  ): Promise<IEvalRun[]> {
    const parsedLimit = limit ? parseInt(limit, 10) : 20;
    return this.runRepo.findByDataset(datasetId, parsedLimit);
  }
}
