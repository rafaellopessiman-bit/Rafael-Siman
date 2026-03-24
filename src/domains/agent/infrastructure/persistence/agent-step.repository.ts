import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AgentStep, AgentStepDocument } from './agent-step.schema';
import { IAgentStepRepository } from '../../domain/repositories/agent-step.repository.interface';
import { CreateAgentStepData } from '../../domain/interfaces/agent-run.interface';

@Injectable()
export class MongooseAgentStepRepository implements IAgentStepRepository {
  constructor(
    @InjectModel(AgentStep.name)
    private readonly model: Model<AgentStepDocument>,
  ) {}

  async create(data: CreateAgentStepData): Promise<AgentStepDocument> {
    return this.model.create({
      ...data,
      schemaVersion: 1,
    });
  }

  async findByRun(runId: string): Promise<AgentStepDocument[]> {
    return this.model.find({ runId }).sort({ stepNumber: 1 });
  }
}
