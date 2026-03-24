/**
 * Contrato de um guardrail de segurança para o agente.
 *
 * Guardrails podem operar em input (mensagem do usuário),
 * output (resposta do agente), ou ambos.
 */
export type GuardrailPhase = 'input' | 'output' | 'both';

export interface GuardrailResult {
  /** Se o conteúdo passou na validação. */
  passed: boolean;
  /** Razão do bloqueio (quando passed=false). */
  reason?: string;
  /** Conteúdo modificado/sanitizado (quando aplicável). */
  modified?: string;
}

export interface GuardrailInfo {
  name: string;
  phase: GuardrailPhase;
  description: string;
  enabled: boolean;
}

export interface IGuardrail {
  readonly name: string;
  readonly phase: GuardrailPhase;
  readonly description: string;
  readonly enabled: boolean;

  validate(content: string): Promise<GuardrailResult>;
}

export const GUARDRAIL_REGISTRY = Symbol('GUARDRAIL_REGISTRY');
