import { IToolExecution, CreateToolExecutionData } from '../interfaces/tool-execution.interface';

export const TOOL_EXECUTION_REPOSITORY = Symbol('TOOL_EXECUTION_REPOSITORY');

export interface IToolExecutionRepository {
  create(data: CreateToolExecutionData): Promise<IToolExecution>;
  findByRun(runId: string): Promise<IToolExecution[]>;
  findByAgent(agentId: string, limit?: number): Promise<IToolExecution[]>;
  findRecent(limit?: number): Promise<IToolExecution[]>;
  countByStatusSince(since: Date): Promise<Record<string, number>>;
  topToolsSince(since: Date, limit?: number): Promise<Array<{ toolName: string; count: number }>>;
}
