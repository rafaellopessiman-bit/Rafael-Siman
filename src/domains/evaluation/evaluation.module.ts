import { Inject, Module, OnModuleInit } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import { EvalDataset, EvalDatasetSchema } from './infrastructure/persistence/eval-dataset.schema';
import { EvalRun, EvalRunSchema } from './infrastructure/persistence/eval-run.schema';
import { MongooseEvalDatasetRepository } from './infrastructure/persistence/eval-dataset.repository';
import { MongooseEvalRunRepository } from './infrastructure/persistence/eval-run.repository';
import { EVAL_DATASET_REPOSITORY } from './domain/repositories/eval-dataset.repository.interface';
import { EVAL_RUN_REPOSITORY } from './domain/repositories/eval-run.repository.interface';
import { EvalEngineService } from './domain/services/eval-engine.service';
import { CriticAgentService } from './domain/services/critic-agent.service';
import { RunEvalUseCase } from './application/use-cases/run-eval.use-case';
import { EvaluationController } from './infrastructure/http/evaluation.controller';
import { CORE_REGRESSION_DATASET } from './data/core-regression.dataset';
import { IEvalDatasetRepository } from './domain/repositories/eval-dataset.repository.interface';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: EvalDataset.name, schema: EvalDatasetSchema },
      { name: EvalRun.name, schema: EvalRunSchema },
    ]),
  ],
  controllers: [EvaluationController],
  providers: [
    {
      provide: EVAL_DATASET_REPOSITORY,
      useClass: MongooseEvalDatasetRepository,
    },
    {
      provide: EVAL_RUN_REPOSITORY,
      useClass: MongooseEvalRunRepository,
    },
    EvalEngineService,
    CriticAgentService,
    RunEvalUseCase,
  ],
  exports: [EvalEngineService, CriticAgentService, EVAL_DATASET_REPOSITORY, EVAL_RUN_REPOSITORY],
})
export class EvaluationModule implements OnModuleInit {
  constructor(
    @Inject(EVAL_DATASET_REPOSITORY)
    private readonly datasetRepo: IEvalDatasetRepository,
  ) {}

  async onModuleInit(): Promise<void> {
    // Seed the core regression dataset on startup (idempotent upsert)
    await this.datasetRepo.upsert(CORE_REGRESSION_DATASET);
  }
}
