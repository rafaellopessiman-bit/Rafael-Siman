import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type PromptTemplateDocument = HydratedDocument<PromptTemplate>;

@Schema({
  collection: 'prompt_templates',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class PromptTemplate {
  @Prop({ required: true, unique: true })
  slug!: string;

  @Prop({ required: true })
  name!: string;

  @Prop({ required: true })
  content!: string;

  @Prop()
  description?: string;

  @Prop({ default: true })
  isActive!: boolean;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const PromptTemplateSchema = SchemaFactory.createForClass(PromptTemplate);

// --- Índices ---

// Lookup por slug (único)
PromptTemplateSchema.index(
  { slug: 1 },
  { unique: true, name: 'prompt_templates_slug_unique_idx' },
);

// Listagem de templates ativos
PromptTemplateSchema.index(
  { isActive: 1, name: 1 },
  { name: 'prompt_templates_isActive_name_idx' },
);
