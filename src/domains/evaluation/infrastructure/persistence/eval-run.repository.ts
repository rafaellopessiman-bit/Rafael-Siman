import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { randomUUID } from 'crypto';
import { IEvalRun } from '../../domain/interfaces/eval-run.interface';
import { IEvalRunRepository } from '../../domain/repositories/eval-run.repository.interface';
import { EvalRun, EvalRunDocument } from './eval-run.schema';

@Injectable()
export class MongooseEvalRunRepository implements IEvalRunRepository {
  constructor(
    @InjectModel(EvalRun.name)
    private readonly model: Model<EvalRunDocument>,
  ) {}

  async create(run: Partial<IEvalRun>): Promise<IEvalRun> {
    const doc = await this.model.create({
      evalRunId: run.id ?? randomUUID(),
      ...run,
      createdAt: new Date(),
      updatedAt: new Date(),
    });
    const plain = doc.toObject();
    return {
      ...plain,
      id: plain.evalRunId,
    } as unknown as IEvalRun;
  }

  async findById(id: string): Promise<IEvalRun | null> {
    const doc = await this.model.findOne({ evalRunId: id }).lean().exec();
    return doc ? this.toInterface(doc) : null;
  }

  async findByDataset(datasetId: string, limit = 20): Promise<IEvalRun[]> {
    const docs = await this.model
      .find({ datasetId })
      .sort({ startedAt: -1 })
      .limit(limit)
      .lean()
      .exec();
    return docs.map((d) => this.toInterface(d));
  }

  async findRecent(limit = 10): Promise<IEvalRun[]> {
    const docs = await this.model
      .find()
      .sort({ startedAt: -1 })
      .limit(limit)
      .lean()
      .exec();
    return docs.map((d) => this.toInterface(d));
  }

  async update(id: string, data: Partial<IEvalRun>): Promise<IEvalRun | null> {
    const doc = await this.model
      .findOneAndUpdate({ evalRunId: id }, { ...data, updatedAt: new Date() }, { new: true })
      .lean()
      .exec();
    return doc ? this.toInterface(doc) : null;
  }

  private toInterface(doc: Record<string, unknown>): IEvalRun {
    return {
      ...doc,
      id: doc['evalRunId'] as string,
    } as unknown as IEvalRun;
  }
}
