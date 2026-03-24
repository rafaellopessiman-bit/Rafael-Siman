import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Schema as MongooseSchema } from 'mongoose';

export type AgentStepDocument = HydratedDocument<AgentStep>;

@Schema({
  collection: 'agent_steps',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class AgentStep {
  @Prop({ required: true })
  runId!: string;

  @Prop({ required: true, min: 1 })
  stepNumber!: number;

  @Prop({
    required: true,
    enum: [
      'llm_call',
      'tool_call',
      'tool_result',
      'guardrail_input',
      'guardrail_output',
      'context_truncation',
      'final_answer',
    ],
  })
  type!: string;

  @Prop({ default: null })
  input?: string;

  @Prop({ default: null })
  output?: string;

  @Prop({ default: 0, min: 0 })
  tokensUsed!: number;

  @Prop({ default: 0, min: 0 })
  latencyMs!: number;

  @Prop({ default: null })
  toolName?: string;

  @Prop({ type: MongooseSchema.Types.Mixed, default: null })
  toolArgs?: Record<string, unknown>;

  @Prop({ type: MongooseSchema.Types.Mixed, default: {} })
  metadata!: Record<string, unknown>;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const AgentStepSchema = SchemaFactory.createForClass(AgentStep);

AgentStepSchema.index(
  { runId: 1, stepNumber: 1 },
  { name: 'agent_steps_runId_stepNumber_idx' },
);
