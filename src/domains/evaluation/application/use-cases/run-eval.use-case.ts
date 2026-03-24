import { Inject, Injectable, NotFoundException } from '@nestjs/common';
import { randomUUID } from 'crypto';
import { IEvalDatasetRepository, EVAL_DATASET_REPOSITORY } from '../../domain/repositories/eval-dataset.repository.interface';
import { IEvalRunRepository, EVAL_RUN_REPOSITORY } from '../../domain/repositories/eval-run.repository.interface';
import { EvalEngineService } from '../../domain/services/eval-engine.service';
import { IEvalRun } from '../../domain/interfaces/eval-run.interface';
import { IEvalScore } from '../../domain/interfaces/eval-score.interface';

export interface RunEvalInput {
  datasetId: string;
  triggeredBy?: string;
}

@Injectable()
export class RunEvalUseCase {
  constructor(
    @Inject(EVAL_DATASET_REPOSITORY)
    private readonly datasetRepo: IEvalDatasetRepository,
    @Inject(EVAL_RUN_REPOSITORY)
    private readonly runRepo: IEvalRunRepository,
    private readonly evalEngine: EvalEngineService,
  ) {}

  async execute(input: RunEvalInput): Promise<IEvalRun> {
    const dataset = await this.datasetRepo.findById(input.datasetId);
    if (!dataset) {
      throw new NotFoundException(`Dataset "${input.datasetId}" not found`);
    }

    const runId = randomUUID();
    const startedAt = new Date();

    // Create run record in pending state
    let run = await this.runRepo.create({
      id: runId,
      datasetId: dataset.id,
      datasetVersion: dataset.version,
      status: 'running',
      triggeredBy: input.triggeredBy ?? 'api',
      totalCases: dataset.cases.length,
      passedCases: 0,
      failedCases: 0,
      startedAt,
      schemaVersion: 1,
    });

    try {
      // Score each case
      const scores: IEvalScore[] = [];
      let passed = 0;
      let failed = 0;

      for (const evalCase of dataset.cases) {
        const score = this.evalEngine.scoreCase(evalCase);
        scores.push(score);
        if (score.overallScore >= 0.7) {
          passed += 1;
        } else {
          failed += 1;
        }
      }

      const aggregateScore = this.evalEngine.aggregate(scores);
      const finishedAt = new Date();

      run = (await this.runRepo.update(runId, {
        status: 'completed',
        passedCases: passed,
        failedCases: failed,
        aggregateScore,
        finishedAt,
        durationMs: finishedAt.getTime() - startedAt.getTime(),
      })) as IEvalRun;

      return run;
    } catch (err) {
      await this.runRepo.update(runId, { status: 'failed', finishedAt: new Date() });
      throw err;
    }
  }
}
