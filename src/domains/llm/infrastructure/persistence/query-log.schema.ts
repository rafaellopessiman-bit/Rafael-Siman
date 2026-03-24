import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type QueryLogDocument = HydratedDocument<QueryLog>;

@Schema({
  collection: 'query_logs',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class QueryLog {
  @Prop({ required: true })
  query!: string;

  @Prop()
  response?: string;

  @Prop()
  model?: string;

  @Prop({ type: [String] })
  sourcesUsed?: string[];

  @Prop({ min: 0 })
  tokensUsed?: number;

  @Prop({ min: 0 })
  latencyMs?: number;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const QueryLogSchema = SchemaFactory.createForClass(QueryLog);

// --- Índices ---

// Ordenação cronológica reversa (queries mais recentes primeiro)
QueryLogSchema.index(
  { createdAt: -1 },
  { name: 'query_logs_createdAt_idx' },
);

// Filtragem por modelo + ordenação cronológica
QueryLogSchema.index(
  { model: 1, createdAt: -1 },
  { name: 'query_logs_model_createdAt_idx' },
);
