import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AgentRun, AgentRunDocument } from './agent-run.schema';
import {
  IAgentRunRepository,
} from '../../domain/repositories/agent-run.repository.interface';
import {
  CreateAgentRunData,
  FinalizeAgentRunData,
} from '../../domain/interfaces/agent-run.interface';

@Injectable()
export class MongooseAgentRunRepository implements IAgentRunRepository {
  constructor(
    @InjectModel(AgentRun.name)
    private readonly model: Model<AgentRunDocument>,
  ) {}

  async create(data: CreateAgentRunData): Promise<AgentRunDocument> {
    return this.model.create({
      ...data,
      totalIterations: 0,
      totalTokens: 0,
      totalLatencyMs: 0,
      toolsUsed: [],
      startedAt: new Date(),
      schemaVersion: 1,
    });
  }

  async finalize(
    runId: string,
    data: FinalizeAgentRunData,
  ): Promise<AgentRunDocument | null> {
    return this.model.findByIdAndUpdate(
      runId,
      {
        $set: {
          status: data.status,
          totalIterations: data.totalIterations,
          totalTokens: data.totalTokens,
          totalLatencyMs: data.totalLatencyMs,
          toolsUsed: data.toolsUsed,
          finalAnswer: data.finalAnswer,
          errorMessage: data.errorMessage,
          finishedAt: new Date(),
          updatedAt: new Date(),
        },
      },
      { new: true },
    );
  }

  async findById(runId: string): Promise<AgentRunDocument | null> {
    return this.model.findById(runId);
  }

  async findByConversation(
    conversationId: string,
    limit = 20,
  ): Promise<AgentRunDocument[]> {
    return this.model
      .find({ conversationId })
      .sort({ createdAt: -1 })
      .limit(limit);
  }

  async findRecent(limit = 20): Promise<AgentRunDocument[]> {
    return this.model.find().sort({ createdAt: -1 }).limit(limit);
  }
}
