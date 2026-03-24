import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { GroqMessage } from '../../../llm/infrastructure/groq/groq-client.service';

const DEFAULT_MAX_CONTEXT_TOKENS = 6000;
const DEFAULT_MAX_MESSAGES = 40;
const MAX_TOOL_OUTPUT_CHARS = 2000;
const CHARS_PER_TOKEN_ESTIMATE = 4;

export interface ContextPrepareResult {
  systemPrompt: string;
  messages: GroqMessage[];
  truncated: boolean;
  estimatedTokens: number;
  originalMessageCount: number;
  finalMessageCount: number;
}

/**
 * Gerencia o context window do agente para prevenir overflow.
 *
 * Estratégias aplicadas em ordem:
 *  1. Tool output trimming — limita cada output de tool a MAX_TOOL_OUTPUT_CHARS
 *  2. Sliding window — mantém apenas as últimas MAX_MESSAGES mensagens
 *  3. Token estimation — estima tokens e descarta mensagens antigas se exceder limite
 *  4. Injeta resumo do contexto descartado como system message auxiliar
 */
@Injectable()
export class ContextManagerService {
  private readonly logger = new Logger(ContextManagerService.name);
  private readonly maxContextTokens: number;
  private readonly maxMessages: number;

  constructor(private readonly configService: ConfigService) {
    this.maxContextTokens = parseInt(
      this.configService.get<string>('AGENT_MAX_CONTEXT_TOKENS', String(DEFAULT_MAX_CONTEXT_TOKENS)),
      10,
    );
    this.maxMessages = parseInt(
      this.configService.get<string>('AGENT_MAX_MESSAGES', String(DEFAULT_MAX_MESSAGES)),
      10,
    );
  }

  prepare(
    messages: GroqMessage[],
    systemPrompt: string,
  ): ContextPrepareResult {
    const originalCount = messages.length;
    let processed = [...messages];
    let truncated = false;

    // 1. Tool output trimming
    processed = processed.map((msg) => {
      if (msg.role === 'tool' && msg.content && msg.content.length > MAX_TOOL_OUTPUT_CHARS) {
        truncated = true;
        return {
          ...msg,
          content: msg.content.substring(0, MAX_TOOL_OUTPUT_CHARS) + '\n[...output truncado]',
        };
      }
      return msg;
    });

    // 2. Sliding window — mantém as últimas N mensagens
    if (processed.length > this.maxMessages) {
      const discarded = processed.length - this.maxMessages;
      processed = processed.slice(-this.maxMessages);
      truncated = true;
      this.logger.log(
        `Context truncado: ${discarded} mensagens antigas removidas (sliding window=${this.maxMessages})`,
      );
    }

    // 3. Token estimation + descarte progressivo
    let estimatedTokens = this.estimateTokens(systemPrompt, processed);

    if (estimatedTokens > this.maxContextTokens) {
      // Descarta mensagens mais antigas (preserva a mais recente de cada role)
      while (
        processed.length > 2 &&
        estimatedTokens > this.maxContextTokens
      ) {
        processed.shift();
        truncated = true;
        estimatedTokens = this.estimateTokens(systemPrompt, processed);
      }
      this.logger.log(
        `Context truncado por tokens: ${estimatedTokens} tokens estimados, ${processed.length} mensagens restantes`,
      );
    }

    // 4. Se houve truncation, injeta contexto auxiliar
    if (truncated && processed.length > 0) {
      const contextNote =
        '[Nota: mensagens anteriores foram resumidas para caber no contexto. ' +
        `Originalmente ${originalCount} mensagens, agora ${processed.length}.]`;
      systemPrompt = systemPrompt + '\n\n' + contextNote;
    }

    return {
      systemPrompt,
      messages: processed,
      truncated,
      estimatedTokens: this.estimateTokens(systemPrompt, processed),
      originalMessageCount: originalCount,
      finalMessageCount: processed.length,
    };
  }

  private estimateTokens(systemPrompt: string, messages: GroqMessage[]): number {
    let totalChars = systemPrompt.length;
    for (const msg of messages) {
      totalChars += (msg.content?.length ?? 0) + 10; // overhead per message
      if (msg.tool_calls) {
        totalChars += JSON.stringify(msg.tool_calls).length;
      }
    }
    return Math.ceil(totalChars / CHARS_PER_TOKEN_ESTIMATE);
  }
}
