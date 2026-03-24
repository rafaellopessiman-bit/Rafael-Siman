import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Schema as MongooseSchema } from 'mongoose';

export type AgentRunDocument = HydratedDocument<AgentRun>;

@Schema({
  collection: 'agent_runs',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class AgentRun {
  @Prop({ required: true })
  conversationId!: string;

  @Prop({
    required: true,
    enum: ['running', 'completed', 'failed', 'timeout'],
    default: 'running',
  })
  status!: string;

  @Prop({ default: null })
  triggeredBy!: string;

  @Prop({ default: 0, min: 0 })
  totalIterations!: number;

  @Prop({ default: 0, min: 0 })
  totalTokens!: number;

  @Prop({ default: 0, min: 0 })
  totalLatencyMs!: number;

  @Prop({ type: [String], default: [] })
  toolsUsed!: string[];

  @Prop({ default: null })
  finalAnswer?: string;

  @Prop({ default: null })
  errorMessage?: string;

  @Prop({ type: Date, default: null })
  startedAt!: Date;

  @Prop({ type: Date, default: null })
  finishedAt?: Date;

  @Prop({ type: MongooseSchema.Types.Mixed, default: {} })
  metadata!: Record<string, unknown>;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const AgentRunSchema = SchemaFactory.createForClass(AgentRun);

AgentRunSchema.index(
  { conversationId: 1, createdAt: -1 },
  { name: 'agent_runs_conversationId_createdAt_idx' },
);

AgentRunSchema.index(
  { status: 1, createdAt: -1 },
  { name: 'agent_runs_status_createdAt_idx' },
);
