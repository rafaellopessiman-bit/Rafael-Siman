import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type AgentMemoryDocument = HydratedDocument<AgentMemory>;

/**
 * Schema Mongoose para memorias resumidas de agentes por conversa.
 *
 * Cada entrada e unica por (conversationId + agentId).
 * O ConversationMemoryService atualiza este registro ao final de cada run,
 * injetando os fatos-chave no system prompt da proxima execucao do agente.
 */
@Schema({
  collection: 'agent_memories',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class AgentMemory {
  @Prop({ required: true })
  conversationId!: string;

  @Prop({ required: true })
  agentId!: string;

  /**
   * Resumo textual da conversa ate o momento, mantido conciso
   * para nao inflar o context window (max ~500 chars recomendado).
   */
  @Prop({ default: '' })
  summary!: string;

  /**
   * Fatos-chave extraidos de runs anteriores desta conversa.
   * Cada item e uma string curta (ex: "usuario perguntou sobre LGPD").
   */
  @Prop({ type: [String], default: [] })
  keyFacts!: string[];

  /** IDs dos runs ja processados nesta memoria. */
  @Prop({ type: [String], default: [] })
  runIds!: string[];

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const AgentMemorySchema = SchemaFactory.createForClass(AgentMemory);

AgentMemorySchema.index(
  { conversationId: 1, agentId: 1 },
  { unique: true, name: 'agent_memories_conversationId_agentId_unique_idx' },
);

AgentMemorySchema.index(
  { conversationId: 1 },
  { name: 'agent_memories_conversationId_idx' },
);
