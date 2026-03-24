import { Injectable, Logger } from '@nestjs/common';
import {
  IGuardrail,
  GuardrailResult,
  GuardrailInfo,
} from '../interfaces/guardrail.interface';

/**
 * Pipeline de guardrails que executa validações de input e output
 * em cadeia. Se qualquer guardrail falhar, o pipeline para e retorna o resultado.
 */
@Injectable()
export class GuardrailPipelineService {
  private readonly logger = new Logger(GuardrailPipelineService.name);
  private readonly guardrails: IGuardrail[] = [];

  /** Registra um guardrail na pipeline. */
  register(guardrail: IGuardrail): void {
    this.guardrails.push(guardrail);
    this.logger.log(`Guardrail registrado: ${guardrail.name} (phase: ${guardrail.phase})`);
  }

  /** Executa guardrails de input (phase 'input' ou 'both'). */
  async runInput(content: string): Promise<GuardrailResult> {
    const inputGuardrails = this.guardrails.filter(
      (g) => g.enabled && (g.phase === 'input' || g.phase === 'both'),
    );

    for (const guardrail of inputGuardrails) {
      const result = await guardrail.validate(content);
      if (!result.passed) {
        this.logger.warn(
          `Guardrail "${guardrail.name}" bloqueou input: ${result.reason}`,
        );
        return result;
      }
    }

    return { passed: true };
  }

  /** Executa guardrails de output (phase 'output' ou 'both'). */
  async runOutput(content: string): Promise<GuardrailResult> {
    const outputGuardrails = this.guardrails.filter(
      (g) => g.enabled && (g.phase === 'output' || g.phase === 'both'),
    );

    let current = content;

    for (const guardrail of outputGuardrails) {
      const result = await guardrail.validate(current);
      if (!result.passed) {
        this.logger.warn(
          `Guardrail "${guardrail.name}" bloqueou output: ${result.reason}`,
        );
        return result;
      }
      // Se o guardrail modificou o conteúdo, usa a versão modificada
      if (result.modified) {
        current = result.modified;
      }
    }

    return { passed: true, modified: current !== content ? current : undefined };
  }

  /** Lista informações de todos os guardrails registrados. */
  listGuardrails(): GuardrailInfo[] {
    return this.guardrails.map((g) => ({
      name: g.name,
      phase: g.phase,
      description: g.description,
      enabled: g.enabled,
    }));
  }
}
