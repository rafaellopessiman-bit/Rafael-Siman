import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Schema as MongooseSchema } from 'mongoose';

export type ToolExecutionDocument = HydratedDocument<ToolExecution>;

@Schema({
  collection: 'tool_executions',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class ToolExecution {
  @Prop({ required: true })
  runId!: string;

  @Prop({ required: true })
  stepId!: string;

  @Prop({ required: true })
  agentId!: string;

  @Prop({ required: true })
  toolName!: string;

  @Prop({ type: MongooseSchema.Types.Mixed, default: {} })
  toolArgs!: Record<string, unknown>;

  @Prop({
    required: true,
    enum: ['success', 'error', 'timeout', 'blocked'],
    default: 'success',
  })
  status!: string;

  @Prop({ default: null })
  result?: string;

  @Prop({ default: null })
  errorMessage?: string;

  @Prop({ required: true, default: 0, min: 0 })
  latencyMs!: number;

  @Prop({ required: true, type: Date })
  executedAt!: Date;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const ToolExecutionSchema = SchemaFactory.createForClass(ToolExecution);

ToolExecutionSchema.index(
  { runId: 1, executedAt: 1 },
  { name: 'tool_executions_runId_executedAt_idx' },
);

ToolExecutionSchema.index(
  { agentId: 1, executedAt: -1 },
  { name: 'tool_executions_agentId_executedAt_idx' },
);

ToolExecutionSchema.index(
  { toolName: 1, status: 1 },
  { name: 'tool_executions_toolName_status_idx' },
);

ToolExecutionSchema.index(
  { executedAt: -1 },
  { name: 'tool_executions_executedAt_idx' },
);
