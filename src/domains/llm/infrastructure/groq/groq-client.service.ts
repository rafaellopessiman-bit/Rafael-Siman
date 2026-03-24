import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { GroqToolDefinition } from '../../../agent/domain/interfaces/agent-tool.interface';

export interface GroqMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | null;
  tool_calls?: GroqToolCall[];
  tool_call_id?: string;
}

export interface GroqToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
}

export interface GroqCompletionResult {
  content: string;
  tokensUsed: number;
  model: string;
  toolCalls?: GroqToolCall[];
}

export interface GroqStreamChunk {
  token: string;
  done: boolean;
}

/**
 * Cliente HTTP para a API Groq (chat completions).
 * Usa fetch nativo (Node 18+) — sem dependência de SDK externo.
 *
 * Endpoint: https://api.groq.com/openai/v1/chat/completions
 * Auth: Bearer {GROQ_API_KEY}
 */
@Injectable()
export class GroqClientService {
  private readonly logger = new Logger(GroqClientService.name);
  private readonly apiKey: string | undefined;
  private readonly model: string;
  private readonly baseUrl = 'https://api.groq.com/openai/v1';

  constructor(private readonly configService: ConfigService) {
    this.apiKey = this.configService.get<string>('GROQ_API_KEY');
    this.model = this.configService.get<string>(
      'GROQ_MODEL',
      'llama-3.3-70b-versatile',
    );
  }

  get isConfigured(): boolean {
    return Boolean(this.apiKey && this.apiKey.trim().length > 0);
  }

  async chatCompletion(
    messages: GroqMessage[],
    maxTokens = 1024,
  ): Promise<GroqCompletionResult> {
    if (!this.isConfigured) {
      this.logger.warn('GROQ_API_KEY não configurado — retornando stub');
      return {
        content: '[LLM não configurado: defina GROQ_API_KEY no .env]',
        tokensUsed: 0,
        model: this.model,
      };
    }

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        max_tokens: maxTokens,
        temperature: 0.2,
      }),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      this.logger.error(
        `Groq API error ${response.status}: ${errorBody}`,
      );
      throw new Error(`Groq API retornou ${response.status}: ${errorBody}`);
    }

    const data = (await response.json()) as {
      choices: Array<{ message: { content: string } }>;
      usage: { total_tokens: number };
      model: string;
    };

    return {
      content: data.choices[0]?.message?.content ?? '',
      tokensUsed: data.usage?.total_tokens ?? 0,
      model: data.model ?? this.model,
    };
  }

  /**
   * Chat completion com suporte a tool/function calling (OpenAI-compatible).
   * Retorna tool_calls quando o LLM decide invocar uma ferramenta.
   */
  async chatCompletionWithTools(
    messages: GroqMessage[],
    tools: GroqToolDefinition[],
    maxTokens = 1024,
  ): Promise<GroqCompletionResult> {
    if (!this.isConfigured) {
      this.logger.warn('GROQ_API_KEY não configurado — retornando stub');
      return {
        content: '[LLM não configurado: defina GROQ_API_KEY no .env]',
        tokensUsed: 0,
        model: this.model,
      };
    }

    const body: Record<string, unknown> = {
      model: this.model,
      messages,
      max_tokens: maxTokens,
      temperature: 0.2,
    };

    if (tools.length > 0) {
      body.tools = tools;
      body.tool_choice = 'auto';
    }

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      this.logger.error(
        `Groq API error ${response.status}: ${errorBody}`,
      );
      throw new Error(`Groq API retornou ${response.status}: ${errorBody}`);
    }

    const data = (await response.json()) as {
      choices: Array<{
        message: {
          content: string | null;
          tool_calls?: GroqToolCall[];
        };
      }>;
      usage: { total_tokens: number };
      model: string;
    };

    const choice = data.choices[0]?.message;

    return {
      content: choice?.content ?? '',
      tokensUsed: data.usage?.total_tokens ?? 0,
      model: data.model ?? this.model,
      toolCalls: choice?.tool_calls,
    };
  }

  /**
   * Chat completion com streaming SSE (OpenAI-compatible).
   * Retorna um AsyncGenerator que yield'a tokens incrementais.
   */
  async *chatCompletionStream(
    messages: GroqMessage[],
    maxTokens = 1024,
  ): AsyncGenerator<GroqStreamChunk> {
    if (!this.isConfigured) {
      yield { token: '[LLM não configurado: defina GROQ_API_KEY no .env]', done: true };
      return;
    }

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages,
        max_tokens: maxTokens,
        temperature: 0.2,
        stream: true,
      }),
    });

    if (!response.ok) {
      const errorBody = await response.text();
      this.logger.error(`Groq streaming error ${response.status}: ${errorBody}`);
      yield { token: `[Erro ${response.status}]`, done: true };
      return;
    }

    const body = response.body;
    if (!body) {
      yield { token: '[Stream body vazio]', done: true };
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    for await (const chunk of body as AsyncIterable<Uint8Array>) {
      buffer += decoder.decode(chunk, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;
        const payload = trimmed.slice(6);
        if (payload === '[DONE]') {
          yield { token: '', done: true };
          return;
        }

        try {
          const parsed = JSON.parse(payload) as {
            choices: Array<{ delta: { content?: string }; finish_reason?: string | null }>;
          };
          const delta = parsed.choices[0]?.delta?.content;
          const finished = parsed.choices[0]?.finish_reason === 'stop';
          if (delta) {
            yield { token: delta, done: false };
          }
          if (finished) {
            yield { token: '', done: true };
            return;
          }
        } catch {
          // Skip malformed SSE lines
        }
      }
    }

    yield { token: '', done: true };
  }
}
