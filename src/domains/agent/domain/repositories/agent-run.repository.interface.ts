import { AgentRunDocument } from '../../infrastructure/persistence/agent-run.schema';
import {
  CreateAgentRunData,
  FinalizeAgentRunData,
} from '../interfaces/agent-run.interface';

export const AGENT_RUN_REPOSITORY = Symbol('AGENT_RUN_REPOSITORY');

export interface IAgentRunRepository {
  create(data: CreateAgentRunData): Promise<AgentRunDocument>;
  finalize(runId: string, data: FinalizeAgentRunData): Promise<AgentRunDocument | null>;
  findById(runId: string): Promise<AgentRunDocument | null>;
  findByConversation(conversationId: string, limit?: number, skip?: number): Promise<AgentRunDocument[]>;
  findRecent(limit?: number, skip?: number): Promise<AgentRunDocument[]>;
  countRecent(): Promise<number>;
  countByConversation(conversationId: string): Promise<number>;
}
