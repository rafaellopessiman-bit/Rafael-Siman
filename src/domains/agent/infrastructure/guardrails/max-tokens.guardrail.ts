import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  IGuardrail,
  GuardrailPhase,
  GuardrailResult,
} from '../../domain/interfaces/guardrail.interface';
import { GuardrailPipelineService } from '../../domain/services/guardrail-pipeline.service';

const DEFAULT_MAX_INPUT_CHARS = 4000;
const DEFAULT_MAX_OUTPUT_CHARS = 8000;

/**
 * Guardrail: max_tokens
 *
 * Limita o tamanho de input e output para controle de custos
 * e prevenção de abuse. Aplicado em ambas as fases (input/output).
 */
@Injectable()
export class MaxTokensGuardrail implements IGuardrail, OnModuleInit {
  readonly name = 'max_tokens';
  readonly phase: GuardrailPhase = 'both';
  readonly description = 'Limita tamanho de input/output para controle de custos e prevenção de abusos.';
  readonly enabled = true;

  private readonly maxInputChars: number;
  private readonly maxOutputChars: number;

  constructor(
    private readonly pipeline: GuardrailPipelineService,
    private readonly configService: ConfigService,
  ) {
    this.maxInputChars = parseInt(
      this.configService.get<string>('AGENT_MAX_INPUT_CHARS', String(DEFAULT_MAX_INPUT_CHARS)),
      10,
    );
    this.maxOutputChars = parseInt(
      this.configService.get<string>('AGENT_MAX_OUTPUT_CHARS', String(DEFAULT_MAX_OUTPUT_CHARS)),
      10,
    );
  }

  onModuleInit(): void {
    this.pipeline.register(this);
  }

  async validate(content: string): Promise<GuardrailResult> {
    // Usa o limite maior (output) como referência genérica;
    // a pipeline chama validate tanto para input quanto output.
    // Para distinguir, verificamos o tamanho contra ambos os limites.
    const maxChars = Math.max(this.maxInputChars, this.maxOutputChars);

    if (content.length > maxChars) {
      return {
        passed: false,
        reason: `Conteúdo excede o limite de ${maxChars} caracteres (${content.length} chars). Reduza o tamanho da mensagem.`,
      };
    }

    return { passed: true };
  }
}
