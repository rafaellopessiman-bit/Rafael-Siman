import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type LlmCacheDocument = HydratedDocument<LlmCache>;

@Schema({
  collection: 'llm_cache',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class LlmCache {
  @Prop({ required: true, unique: true })
  queryHash!: string;

  @Prop({ required: true })
  response!: string;

  @Prop()
  model?: string;

  @Prop({ default: 0, min: 0 })
  hitCount!: number;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const LlmCacheSchema = SchemaFactory.createForClass(LlmCache);

// --- Índices ---

// Lookup rápido por hash — unique garante dedup
LlmCacheSchema.index(
  { queryHash: 1 },
  { unique: true, name: 'llm_cache_queryHash_unique_idx' },
);

// TTL: expira cache após 24h (86400s)
LlmCacheSchema.index(
  { createdAt: 1 },
  { expireAfterSeconds: 86400, name: 'llm_cache_createdAt_ttl_idx' },
);
