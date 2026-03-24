import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { LlmCache, LlmCacheDocument } from './llm-cache.schema';
import { ILlmCacheRepository } from '../../domain/repositories/llm-cache.repository.interface';

@Injectable()
export class MongooseLlmCacheRepository implements ILlmCacheRepository {
  constructor(
    @InjectModel(LlmCache.name)
    private readonly cacheModel: Model<LlmCacheDocument>,
  ) {}

  async getCached(queryHash: string): Promise<string | null> {
    const cached = await this.cacheModel.findOneAndUpdate(
      { queryHash },
      { $inc: { hitCount: 1 }, $set: { updatedAt: new Date() } },
      { new: true },
    );
    return cached?.response ?? null;
  }

  async setCache(
    queryHash: string,
    response: string,
    model: string,
  ): Promise<void> {
    await this.cacheModel.updateOne(
      { queryHash },
      {
        $set: { response, model, updatedAt: new Date() },
        $setOnInsert: { hitCount: 0, schemaVersion: 1, createdAt: new Date() },
      },
      { upsert: true },
    );
  }
}
