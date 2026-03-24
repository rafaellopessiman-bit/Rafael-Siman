import { IEvalCase } from './eval-case.interface';

/**
 * Dataset de casos de avaliacao.
 *
 * Um dataset e uma colecao nomeada e versionada de EvalCases.
 * `isRegression` indica que o dataset deve rodar em todo CI.
 */
export interface IEvalDataset {
  id: string;
  name: string;
  description: string;
  version: string;
  isRegression: boolean;
  cases: IEvalCase[];
  createdAt: Date;
  updatedAt: Date;
  schemaVersion: number;
}
