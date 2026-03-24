import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { QueryLog, QueryLogDocument } from './query-log.schema';
import {
  IQueryLogRepository,
  CreateQueryLogData,
} from '../../domain/repositories/query-log.repository.interface';

@Injectable()
export class MongooseQueryLogRepository implements IQueryLogRepository {
  constructor(
    @InjectModel(QueryLog.name)
    private readonly logModel: Model<QueryLogDocument>,
  ) {}

  async logQuery(data: CreateQueryLogData): Promise<void> {
    await this.logModel.create({
      ...data,
      schemaVersion: 1,
    });
  }
}
