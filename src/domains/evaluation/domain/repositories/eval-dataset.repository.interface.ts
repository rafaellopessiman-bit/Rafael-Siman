import { IEvalDataset } from '../interfaces/eval-dataset.interface';

export const EVAL_DATASET_REPOSITORY = Symbol('EVAL_DATASET_REPOSITORY');

export interface IEvalDatasetRepository {
  findById(id: string): Promise<IEvalDataset | null>;
  findAll(): Promise<IEvalDataset[]>;
  findRegression(): Promise<IEvalDataset[]>;
  upsert(dataset: IEvalDataset): Promise<IEvalDataset>;
}
