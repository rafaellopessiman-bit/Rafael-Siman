import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AgentDefinition, AgentDefinitionDocument } from './agent-definition.schema';
import {
  IAgentDefinitionRepository,
} from '../../domain/repositories/agent-definition.repository.interface';
import { IAgentDefinition } from '../../domain/interfaces/agent-definition.interface';

@Injectable()
export class MongooseAgentDefinitionRepository implements IAgentDefinitionRepository {
  constructor(
    @InjectModel(AgentDefinition.name)
    private readonly model: Model<AgentDefinitionDocument>,
  ) {}

  async findById(id: string): Promise<IAgentDefinition | null> {
    const doc = await this.model.findOne({ id }).lean();
    return doc ? this.toEntity(doc) : null;
  }

  async findAll(): Promise<IAgentDefinition[]> {
    const docs = await this.model.find().lean();
    return docs.map((d) => this.toEntity(d));
  }

  async findActive(): Promise<IAgentDefinition[]> {
    const docs = await this.model.find({ isActive: true }).lean();
    return docs.map((d) => this.toEntity(d));
  }

  async upsert(definition: IAgentDefinition): Promise<IAgentDefinition> {
    const doc = await this.model.findOneAndUpdate(
      { id: definition.id },
      { $set: { ...definition, schemaVersion: 1 } },
      { upsert: true, new: true },
    ).lean();
    return this.toEntity(doc!);
  }

  private toEntity(doc: Record<string, unknown>): IAgentDefinition {
    return {
      id: doc.id as string,
      name: doc.name as string,
      description: doc.description as string,
      version: doc.version as string,
      capabilities: (doc.capabilities as string[]) as IAgentDefinition['capabilities'],
      allowedTools: doc.allowedTools as string[],
      handoffTargets: doc.handoffTargets as string[],
      systemPrompt: doc.systemPrompt as string,
      isActive: doc.isActive as boolean,
    };
  }
}
