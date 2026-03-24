import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AgentMemory, AgentMemoryDocument } from './agent-memory.schema';
import {
  IAgentMemoryRepository,
  AgentMemoryData,
} from '../../domain/repositories/agent-memory.repository.interface';

@Injectable()
export class MongooseAgentMemoryRepository implements IAgentMemoryRepository {
  constructor(
    @InjectModel(AgentMemory.name)
    private readonly model: Model<AgentMemoryDocument>,
  ) {}

  async findByConversationAndAgent(
    conversationId: string,
    agentId: string,
  ): Promise<AgentMemoryData | null> {
    const doc = await this.model.findOne({ conversationId, agentId }).lean();
    return doc ? this.toData(doc) : null;
  }

  async upsert(memory: AgentMemoryData): Promise<AgentMemoryData> {
    const doc = await this.model.findOneAndUpdate(
      { conversationId: memory.conversationId, agentId: memory.agentId },
      { $set: { ...memory, schemaVersion: 1 } },
      { upsert: true, new: true },
    ).lean();
    return this.toData(doc!);
  }

  async findRecent(
    conversationId: string,
    limit = 5,
  ): Promise<AgentMemoryData[]> {
    const docs = await this.model
      .find({ conversationId })
      .sort({ updatedAt: -1 })
      .limit(limit)
      .lean();
    return docs.map((d) => this.toData(d));
  }

  private toData(doc: Record<string, unknown>): AgentMemoryData {
    return {
      conversationId: doc.conversationId as string,
      agentId: doc.agentId as string,
      summary: doc.summary as string,
      keyFacts: doc.keyFacts as string[],
      runIds: doc.runIds as string[],
    };
  }
}
