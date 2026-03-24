import { Injectable, OnModuleInit } from '@nestjs/common';
import {
  IGuardrail,
  GuardrailPhase,
  GuardrailResult,
} from '../../domain/interfaces/guardrail.interface';
import { GuardrailPipelineService } from '../../domain/services/guardrail-pipeline.service';

/**
 * Guardrail: pii_detector
 *
 * Detecta e sanitiza dados pessoais sensíveis no output do agente:
 * - CPF
 * - Emails
 * - Telefones brasileiros
 * - Números de cartão de crédito
 */
const PII_PATTERNS: Array<{ pattern: RegExp; label: string; replacement: string }> = [
  {
    pattern: /\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[.\s-]?\d{2}\b/g,
    label: 'CPF',
    replacement: '[CPF REDACTED]',
  },
  {
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    label: 'email',
    replacement: '[EMAIL REDACTED]',
  },
  {
    pattern: /\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[-.\s]?\d{4}\b/g,
    label: 'telefone',
    replacement: '[TELEFONE REDACTED]',
  },
  {
    pattern: /\b(?:\d{4}[-.\s]?){3}\d{4}\b/g,
    label: 'cartão de crédito',
    replacement: '[CARTAO REDACTED]',
  },
];

@Injectable()
export class PiiDetectorGuardrail implements IGuardrail, OnModuleInit {
  readonly name = 'pii_detector';
  readonly phase: GuardrailPhase = 'output';
  readonly description = 'Detecta e sanitiza dados pessoais (CPF, email, telefone, cartão) no output do agente.';
  readonly enabled = true;

  constructor(private readonly pipeline: GuardrailPipelineService) {}

  onModuleInit(): void {
    this.pipeline.register(this);
  }

  async validate(content: string): Promise<GuardrailResult> {
    let sanitized = content;
    let hasPii = false;

    for (const { pattern, replacement } of PII_PATTERNS) {
      // Reset regex due to global flag
      pattern.lastIndex = 0;
      if (pattern.test(sanitized)) {
        hasPii = true;
        pattern.lastIndex = 0;
        sanitized = sanitized.replace(pattern, replacement);
      }
    }

    if (hasPii) {
      return {
        passed: true,
        modified: sanitized,
      };
    }

    return { passed: true };
  }
}
