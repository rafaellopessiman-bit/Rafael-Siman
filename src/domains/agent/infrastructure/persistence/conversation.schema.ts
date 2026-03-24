import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Schema as MongooseSchema } from 'mongoose';

export type ConversationDocument = HydratedDocument<Conversation>;

export class ConversationMessage {
  @Prop({ required: true, enum: ['system', 'user', 'assistant', 'tool'] })
  role!: string;

  @Prop({ type: String, default: null })
  content!: string | null;

  @Prop()
  toolCallId?: string;

  @Prop({ type: MongooseSchema.Types.Mixed })
  toolCalls?: Array<{
    id: string;
    type: string;
    function: { name: string; arguments: string };
  }>;

  @Prop({ default: () => new Date() })
  timestamp!: Date;
}

const ConversationMessageSchema = SchemaFactory.createForClass(ConversationMessage);

@Schema({
  collection: 'conversations',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class Conversation {
  @Prop({ required: true })
  title!: string;

  @Prop()
  systemPrompt?: string;

  @Prop({ type: [ConversationMessageSchema], default: [] })
  messages!: ConversationMessage[];

  @Prop({ default: 0, min: 0 })
  totalTokens!: number;

  @Prop({ default: 0, min: 0 })
  messageCount!: number;

  @Prop({ default: true })
  isActive!: boolean;

  @Prop({ type: MongooseSchema.Types.Mixed, default: {} })
  metadata!: Record<string, unknown>;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const ConversationSchema = SchemaFactory.createForClass(Conversation);

// --- Índices ---

// Listagem cronológica reversa
ConversationSchema.index(
  { createdAt: -1 },
  { name: 'conversations_createdAt_idx' },
);

// Filtragem por status ativo + data
ConversationSchema.index(
  { isActive: 1, updatedAt: -1 },
  { name: 'conversations_isActive_updatedAt_idx' },
);
