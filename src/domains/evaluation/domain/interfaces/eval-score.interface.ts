/**
 * Score composto calculado pelo EvalEngine por dimensao.
 *
 * Scores vao de 0.0 a 1.0, onde 1.0 e perfeito.
 * `null` indica que a dimensao nao foi avaliada para aquele caso.
 */
export interface IEvalScore {
  /** Resposta gerada e baseada nos documentos recuperados? */
  faithfulness: number | null;
  /** Resposta cobre a intencao da pergunta? */
  relevance: number | null;
  /** Resposta aborda todos os aspectos necessarios? */
  completeness: number | null;
  /** Proporcao de afirmacoes com citacao de fonte verificavel. */
  citationCoverage: number | null;
  /** Ferramentas invocadas funcionaram sem erro? */
  toolSuccess: number | null;
  /** Guardrails nao foram violados? (1 = sem violacoes, 0 = bloqueado) */
  guardrailCompliance: number | null;
  /** Latencia total ficou dentro do orcamento definido no caso? */
  latencyBudget: number | null;
  /** Pontuacao agregada ponderada (0.0 a 1.0). */
  overallScore: number;
}
