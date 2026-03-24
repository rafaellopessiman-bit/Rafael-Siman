import { IEvalScore } from './eval-score.interface';

export type EvalRunStatus = 'pending' | 'running' | 'completed' | 'failed';

/**
 * Uma execucao completa de um dataset de avaliacao.
 *
 * Persiste no MongoDB para comparacao historica entre releases.
 * `caseResults` e um array de IDs dos EvalCase com seus resultados.
 */
export interface IEvalRun {
  id: string;
  datasetId: string;
  datasetVersion: string;
  status: EvalRunStatus;
  triggeredBy: string;
  totalCases: number;
  passedCases: number;
  failedCases: number;
  aggregateScore: IEvalScore;
  startedAt: Date;
  finishedAt?: Date;
  durationMs?: number;
  createdAt: Date;
  updatedAt: Date;
  schemaVersion: number;
}
