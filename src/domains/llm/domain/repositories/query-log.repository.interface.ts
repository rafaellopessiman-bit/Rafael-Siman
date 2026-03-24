import { QueryLog } from '../../infrastructure/persistence/query-log.schema';

export const QUERY_LOG_REPOSITORY = Symbol('QUERY_LOG_REPOSITORY');

export type CreateQueryLogData = Pick<QueryLog, 'query'> &
  Partial<Pick<QueryLog, 'response' | 'model' | 'sourcesUsed' | 'tokensUsed' | 'latencyMs'>>;

export interface IQueryLogRepository {
  logQuery(data: CreateQueryLogData): Promise<void>;
}
