import { IEvalScore } from './eval-score.interface';

/**
 * Um caso de avaliacao individual dentro de um dataset.
 *
 * `input` e a pergunta enviada ao agente.
 * `expectedKeywords` sao termos que DEVEM aparecer na resposta ideal.
 * `forbiddenKeywords` sao termos que NAO devem aparecer (ex.: dados inventados).
 * `expectedAgents` lista os agentes esperados no caminho de execucao.
 * `latencyBudgetMs` define o limite aceitavel de latencia para o caso.
 */
export interface IEvalCase {
  id: string;
  datasetId: string;
  input: string;
  expectedKeywords: string[];
  forbiddenKeywords: string[];
  expectedAgents: string[];
  requiresCitations: boolean;
  latencyBudgetMs: number;
  /** Preenchido apos execucao de uma eval run. */
  actualOutput?: string;
  actualAgents?: string[];
  actualLatencyMs?: number;
  score?: IEvalScore;
  passed?: boolean;
}
