import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { ToolExecution, ToolExecutionDocument } from './tool-execution.schema';
import {
  IToolExecutionRepository,
} from '../../domain/repositories/tool-execution.repository.interface';
import {
  IToolExecution,
  CreateToolExecutionData,
} from '../../domain/interfaces/tool-execution.interface';
import { randomUUID } from 'crypto';

@Injectable()
export class MongooseToolExecutionRepository implements IToolExecutionRepository {
  constructor(
    @InjectModel(ToolExecution.name)
    private readonly model: Model<ToolExecutionDocument>,
  ) {}

  async create(data: CreateToolExecutionData): Promise<IToolExecution> {
    const doc = await this.model.create({
      ...data,
      schemaVersion: 1,
    });
    return {
      id: doc._id.toString(),
      runId: doc.runId,
      stepId: doc.stepId,
      agentId: doc.agentId,
      toolName: doc.toolName,
      toolArgs: doc.toolArgs,
      status: doc.status as IToolExecution['status'],
      result: doc.result,
      errorMessage: doc.errorMessage,
      latencyMs: doc.latencyMs,
      executedAt: doc.executedAt,
      schemaVersion: doc.schemaVersion,
    };
  }

  async findByRun(runId: string): Promise<IToolExecution[]> {
    const docs = await this.model.find({ runId }).sort({ executedAt: 1 }).lean();
    return docs.map((d) => this.toEntity(d));
  }

  async findByAgent(agentId: string, limit = 50): Promise<IToolExecution[]> {
    const docs = await this.model.find({ agentId }).sort({ executedAt: -1 }).limit(limit).lean();
    return docs.map((d) => this.toEntity(d));
  }

  async findRecent(limit = 50): Promise<IToolExecution[]> {
    const docs = await this.model.find().sort({ executedAt: -1 }).limit(limit).lean();
    return docs.map((d) => this.toEntity(d));
  }

  async countByStatusSince(since: Date): Promise<Record<string, number>> {
    const agg = await this.model.aggregate<{ _id: string; count: number }>([
      { $match: { executedAt: { $gte: since } } },
      { $group: { _id: '$status', count: { $sum: 1 } } },
    ]);
    const result: Record<string, number> = {};
    for (const item of agg) {
      result[item._id] = item.count;
    }
    return result;
  }

  async topToolsSince(
    since: Date,
    limit = 5,
  ): Promise<Array<{ toolName: string; count: number }>> {
    return this.model.aggregate<{ toolName: string; count: number }>([
      { $match: { executedAt: { $gte: since } } },
      { $group: { _id: '$toolName', count: { $sum: 1 } } },
      { $sort: { count: -1 } },
      { $limit: limit },
      { $project: { _id: 0, toolName: '$_id', count: 1 } },
    ]);
  }

  private toEntity(doc: Record<string, unknown>): IToolExecution {
    return {
      id: (doc['_id'] as object).toString(),
      runId: doc['runId'] as string,
      stepId: doc['stepId'] as string,
      agentId: doc['agentId'] as string,
      toolName: doc['toolName'] as string,
      toolArgs: (doc['toolArgs'] as Record<string, unknown>) ?? {},
      status: doc['status'] as IToolExecution['status'],
      result: doc['result'] as string | undefined,
      errorMessage: doc['errorMessage'] as string | undefined,
      latencyMs: doc['latencyMs'] as number,
      executedAt: doc['executedAt'] as Date,
      schemaVersion: doc['schemaVersion'] as number,
    };
  }
}

/** In-memory stub for testing — not exported from the module */
export class InMemoryToolExecutionRepository implements IToolExecutionRepository {
  private readonly items: IToolExecution[] = [];

  async create(data: CreateToolExecutionData): Promise<IToolExecution> {
    const item = { id: randomUUID(), ...data, schemaVersion: 1 } as IToolExecution;
    this.items.push(item);
    return item;
  }

  async findByRun(runId: string): Promise<IToolExecution[]> {
    return this.items.filter((i) => i.runId === runId);
  }

  async findByAgent(agentId: string, limit = 50): Promise<IToolExecution[]> {
    return this.items.filter((i) => i.agentId === agentId).slice(0, limit);
  }

  async findRecent(limit = 50): Promise<IToolExecution[]> {
    return [...this.items].reverse().slice(0, limit);
  }

  async countByStatusSince(_since: Date): Promise<Record<string, number>> {
    const result: Record<string, number> = {};
    for (const item of this.items) {
      result[item.status] = (result[item.status] ?? 0) + 1;
    }
    return result;
  }

  async topToolsSince(_since: Date, limit = 5): Promise<Array<{ toolName: string; count: number }>> {
    const counts: Record<string, number> = {};
    for (const item of this.items) {
      counts[item.toolName] = (counts[item.toolName] ?? 0) + 1;
    }
    return Object.entries(counts)
      .map(([toolName, count]) => ({ toolName, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  }
}
