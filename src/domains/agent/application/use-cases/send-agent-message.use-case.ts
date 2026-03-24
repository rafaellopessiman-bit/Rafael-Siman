import { Injectable, Inject, NotFoundException, Logger } from '@nestjs/common';
import {
  CONVERSATION_REPOSITORY,
  IConversationRepository,
} from '../../domain/repositories/conversation.repository.interface';
import {
  PROMPT_TEMPLATE_REPOSITORY,
  IPromptTemplateRepository,
} from '../../domain/repositories/prompt-template.repository.interface';
import { AgentLoopService } from '../../domain/services/agent-loop.service';
import {
  SendMessageDto,
  AgentResponse,
} from '../dtos/agent.dto';
import { GroqMessage } from '../../../llm/infrastructure/groq/groq-client.service';

/**
 * Envia uma mensagem para uma conversa existente e executa o loop do agente.
 *
 * Fluxo:
 *  1. Recupera conversa + histórico
 *  2. Persiste mensagem do usuário
 *  3. Monta contexto (histórico → GroqMessage[])
 *  4. Executa AgentLoopService (ReAct com tools)
 *  5. Persiste resposta do assistente
 *  6. Retorna resultado
 */
@Injectable()
export class SendAgentMessageUseCase {
  private readonly logger = new Logger(SendAgentMessageUseCase.name);

  constructor(
    @Inject(CONVERSATION_REPOSITORY)
    private readonly conversationRepo: IConversationRepository,
    @Inject(PROMPT_TEMPLATE_REPOSITORY)
    private readonly templateRepo: IPromptTemplateRepository,
    private readonly agentLoop: AgentLoopService,
  ) {}

  async execute(
    conversationId: string,
    dto: SendMessageDto,
  ): Promise<AgentResponse> {
    // 1. Recupera conversa
    const conversation =
      await this.conversationRepo.findById(conversationId);
    if (!conversation) {
      throw new NotFoundException(
        `Conversa "${conversationId}" não encontrada`,
      );
    }

    // 2. Persiste mensagem do usuário
    await this.conversationRepo.appendMessage(conversationId, {
      role: 'user',
      content: dto.message,
    });

    // 3. Resolve system prompt (slug de template ou literal)
    let systemPrompt = conversation.systemPrompt;
    if (systemPrompt && !systemPrompt.includes(' ')) {
      // Parece um slug — tenta carregar template
      const template = await this.templateRepo.findBySlug(systemPrompt);
      if (template) {
        systemPrompt = template.content;
      }
    }

    // 4. Monta histórico para o LLM
    const history: GroqMessage[] = conversation.messages.map((msg) => ({
      role: msg.role as GroqMessage['role'],
      content: msg.content,
      tool_calls: msg.toolCalls as GroqMessage['tool_calls'],
      tool_call_id: msg.toolCallId,
    }));

    // Adiciona a mensagem atual
    history.push({ role: 'user', content: dto.message });

    // 5. Executa agent loop
    this.logger.log(
      `Executando agent loop para conversa ${conversationId} (${history.length} mensagens)`,
    );

    const result = await this.agentLoop.run(history, systemPrompt, {
      conversationId,
      triggeredBy: 'api',
    });

    // 6. Persiste resposta do assistente
    await this.conversationRepo.appendMessage(conversationId, {
      role: 'assistant',
      content: result.answer,
    });

    await this.conversationRepo.addTokens(
      conversationId,
      result.totalTokens,
    );

    return {
      conversationId,
      answer: result.answer,
      runId: result.runId,
      toolsUsed: result.toolsUsed,
      iterations: result.iterations,
      totalTokens: result.totalTokens,
      latencyMs: result.latencyMs,
    };
  }
}
