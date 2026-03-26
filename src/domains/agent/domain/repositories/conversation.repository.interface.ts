import { ConversationDocument } from '../../infrastructure/persistence/conversation.schema';

export const CONVERSATION_REPOSITORY = Symbol('CONVERSATION_REPOSITORY');

export interface CreateConversationData {
  title: string;
  systemPrompt?: string;
  metadata?: Record<string, unknown>;
}

export interface AppendMessageData {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | null;
  toolCallId?: string;
  toolCalls?: Array<{
    id: string;
    type: string;
    function: { name: string; arguments: string };
  }>;
}

export interface IConversationRepository {
  create(data: CreateConversationData): Promise<ConversationDocument>;
  findById(id: string): Promise<ConversationDocument | null>;
  findAll(onlyActive?: boolean): Promise<ConversationDocument[]>;
  findPaginated(skip: number, limit: number, onlyActive?: boolean): Promise<ConversationDocument[]>;
  countAll(onlyActive?: boolean): Promise<number>;
  appendMessage(
    conversationId: string,
    message: AppendMessageData,
  ): Promise<ConversationDocument | null>;
  addTokens(
    conversationId: string,
    tokens: number,
  ): Promise<void>;
  archive(conversationId: string): Promise<void>;
}
