import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';
import { AgentCapability } from '../../domain/interfaces/agent-capability.interface';

export type AgentDefinitionDocument = HydratedDocument<AgentDefinition>;

/**
 * Schema Mongoose para definicoes de agentes.
 *
 * Persiste as definicoes versionadas no MongoDB (collection: agent_definitions).
 * O AgentRegistryService carrega estas definicoes no startup e mantém cache in-memory.
 */
@Schema({
  collection: 'agent_definitions',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class AgentDefinition {
  @Prop({ required: true, unique: true })
  id!: string;

  @Prop({ required: true })
  name!: string;

  @Prop({ required: true })
  description!: string;

  @Prop({ required: true, default: '1.0.0' })
  version!: string;

  @Prop({
    type: [String],
    enum: Object.values(AgentCapability),
    default: [],
  })
  capabilities!: AgentCapability[];

  @Prop({ type: [String], default: [] })
  allowedTools!: string[];

  @Prop({ type: [String], default: [] })
  handoffTargets!: string[];

  @Prop({ required: true, type: String })
  systemPrompt!: string;

  @Prop({ default: true })
  isActive!: boolean;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const AgentDefinitionSchema = SchemaFactory.createForClass(AgentDefinition);

AgentDefinitionSchema.index(
  { id: 1 },
  { unique: true, name: 'agent_definitions_id_unique_idx' },
);

AgentDefinitionSchema.index(
  { isActive: 1 },
  { name: 'agent_definitions_isActive_idx' },
);
