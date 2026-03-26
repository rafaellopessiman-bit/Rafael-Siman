import { IEvalRun } from '../interfaces/eval-run.interface';

export const EVAL_RUN_REPOSITORY = Symbol('EVAL_RUN_REPOSITORY');

export interface IEvalRunRepository {
  create(run: Partial<IEvalRun>): Promise<IEvalRun>;
  findById(id: string): Promise<IEvalRun | null>;
  findByDataset(datasetId: string, limit?: number, skip?: number): Promise<IEvalRun[]>;
  findRecent(limit?: number, skip?: number): Promise<IEvalRun[]>;
  update(id: string, data: Partial<IEvalRun>): Promise<IEvalRun | null>;
  countRecent(): Promise<number>;
  countByDataset(datasetId: string): Promise<number>;
}
