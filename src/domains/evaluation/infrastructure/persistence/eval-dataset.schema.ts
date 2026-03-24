import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

// ─── EvalCase sub-document ──────────────────────────────────────────────────

@Schema({ _id: false })
class EvalCaseSubDoc {
  @Prop({ required: true })
  id!: string;

  @Prop({ required: true })
  datasetId!: string;

  @Prop({ required: true })
  input!: string;

  @Prop({ type: [String], default: [] })
  expectedKeywords!: string[];

  @Prop({ type: [String], default: [] })
  forbiddenKeywords!: string[];

  @Prop({ type: [String], default: [] })
  expectedAgents!: string[];

  @Prop({ default: false })
  requiresCitations!: boolean;

  @Prop({ default: 5000 })
  latencyBudgetMs!: number;
}

const EvalCaseSubDocSchema = SchemaFactory.createForClass(EvalCaseSubDoc);

// ─── EvalDataset root document ──────────────────────────────────────────────

export type EvalDatasetDocument = HydratedDocument<EvalDataset>;

@Schema({
  collection: 'eval_datasets',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class EvalDataset {
  @Prop({ required: true, unique: true })
  evalDatasetId!: string;

  @Prop({ required: true })
  name!: string;

  @Prop({ default: '' })
  description!: string;

  @Prop({ default: '1.0.0' })
  version!: string;

  @Prop({ default: false })
  isRegression!: boolean;

  @Prop({ type: [EvalCaseSubDocSchema], default: [] })
  cases!: EvalCaseSubDoc[];

  @Prop({ default: 1 })
  schemaVersion!: number;
}

export const EvalDatasetSchema = SchemaFactory.createForClass(EvalDataset);

EvalDatasetSchema.index({ evalDatasetId: 1 }, { unique: true, name: 'eval_datasets_id_unique_idx' });
EvalDatasetSchema.index({ isRegression: 1 }, { name: 'eval_datasets_isRegression_idx' });
