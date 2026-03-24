import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { IEvalDataset } from '../../domain/interfaces/eval-dataset.interface';
import { IEvalDatasetRepository } from '../../domain/repositories/eval-dataset.repository.interface';
import { EvalDataset, EvalDatasetDocument } from './eval-dataset.schema';

@Injectable()
export class MongooseEvalDatasetRepository implements IEvalDatasetRepository {
  constructor(
    @InjectModel(EvalDataset.name)
    private readonly model: Model<EvalDatasetDocument>,
  ) {}

  async findById(id: string): Promise<IEvalDataset | null> {
    const doc = await this.model.findOne({ evalDatasetId: id }).lean().exec();
    return doc ? this.toInterface(doc) : null;
  }

  async findAll(): Promise<IEvalDataset[]> {
    const docs = await this.model.find().sort({ createdAt: -1 }).lean().exec();
    return docs.map((d) => this.toInterface(d));
  }

  async findRegression(): Promise<IEvalDataset[]> {
    const docs = await this.model.find({ isRegression: true }).lean().exec();
    return docs.map((d) => this.toInterface(d));
  }

  async upsert(dataset: IEvalDataset): Promise<IEvalDataset> {
    const doc = await this.model
      .findOneAndUpdate(
        { evalDatasetId: dataset.id },
        { evalDatasetId: dataset.id, ...dataset, updatedAt: new Date() },
        { upsert: true, new: true },
      )
      .lean()
      .exec();
    return this.toInterface(doc);
  }

  private toInterface(doc: Record<string, unknown>): IEvalDataset {
    return {
      ...doc,
      id: doc['evalDatasetId'] as string,
    } as unknown as IEvalDataset;
  }
}
