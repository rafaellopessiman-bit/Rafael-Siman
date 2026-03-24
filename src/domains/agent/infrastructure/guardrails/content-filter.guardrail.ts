import { Injectable, OnModuleInit } from '@nestjs/common';
import {
  IGuardrail,
  GuardrailPhase,
  GuardrailResult,
} from '../../domain/interfaces/guardrail.interface';
import { GuardrailPipelineService } from '../../domain/services/guardrail-pipeline.service';

/**
 * Guardrail: content_filter
 *
 * Filtra conteúdo potencialmente perigoso ou fora do escopo:
 * - Tentativas de prompt injection
 * - Instruções para ignorar system prompt
 * - Comandos de sistema / shell injection
 */
const BLOCKED_PATTERNS = [
  /ignore\s+(previous|all|your)\s+(instructions?|prompts?|rules?)/i,
  /disregard\s+(all|your)\s+(instructions?|prompts?|rules?)/i,
  /you\s+are\s+now\s+(a|an)\s+/i,
  /pretend\s+(you|that)\s+(are|you)/i,
  /system\s*:\s*override/i,
  /\bDROP\s+TABLE\b/i,
  /\bDELETE\s+FROM\b/i,
  /;\s*(rm|del|format|shutdown|reboot)\s/i,
  /\b(exec|eval|spawn)\s*\(/i,
];

@Injectable()
export class ContentFilterGuardrail implements IGuardrail, OnModuleInit {
  readonly name = 'content_filter';
  readonly phase: GuardrailPhase = 'input';
  readonly description = 'Filtra tentativas de prompt injection e comandos perigosos no input do usuário.';
  readonly enabled = true;

  constructor(private readonly pipeline: GuardrailPipelineService) {}

  onModuleInit(): void {
    this.pipeline.register(this);
  }

  async validate(content: string): Promise<GuardrailResult> {
    for (const pattern of BLOCKED_PATTERNS) {
      if (pattern.test(content)) {
        return {
          passed: false,
          reason: `Conteúdo bloqueado: padrão suspeito detectado (${this.name}).`,
        };
      }
    }
    return { passed: true };
  }
}
