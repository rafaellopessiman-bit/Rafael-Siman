import { AgentStepDocument } from '../../infrastructure/persistence/agent-step.schema';
import { CreateAgentStepData } from '../interfaces/agent-run.interface';

export const AGENT_STEP_REPOSITORY = Symbol('AGENT_STEP_REPOSITORY');

export interface IAgentStepRepository {
  create(data: CreateAgentStepData): Promise<AgentStepDocument>;
  findByRun(runId: string): Promise<AgentStepDocument[]>;
}
