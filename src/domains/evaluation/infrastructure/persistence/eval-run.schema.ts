import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';
import { EvalRunStatus } from '../../domain/interfaces/eval-run.interface';

// ─── Aggregate score sub-document ───────────────────────────────────────────

@Schema({ _id: false })
class AggregateScoreSubDoc {
  @Prop({ type: Number, default: null })
  faithfulness?: number | null;

  @Prop({ type: Number, default: null })
  relevance?: number | null;

  @Prop({ type: Number, default: null })
  completeness?: number | null;

  @Prop({ type: Number, default: null })
  citationCoverage?: number | null;

  @Prop({ type: Number, default: null })
  toolSuccess?: number | null;

  @Prop({ type: Number, default: null })
  guardrailCompliance?: number | null;

  @Prop({ type: Number, default: null })
  latencyBudget?: number | null;

  @Prop({ default: 0 })
  overallScore!: number;
}

const AggregateScoreSubDocSchema = SchemaFactory.createForClass(AggregateScoreSubDoc);

// ─── EvalRun root document ───────────────────────────────────────────────────

export type EvalRunDocument = HydratedDocument<EvalRun>;

@Schema({
  collection: 'eval_runs',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class EvalRun {
  @Prop({ required: true, unique: true })
  evalRunId!: string;

  @Prop({ required: true })
  datasetId!: string;

  @Prop({ required: true })
  datasetVersion!: string;

  @Prop({
    type: String,
    enum: ['pending', 'running', 'completed', 'failed'],
    default: 'pending',
  })
  status!: EvalRunStatus;

  @Prop({ default: 'api' })
  triggeredBy!: string;

  @Prop({ default: 0 })
  totalCases!: number;

  @Prop({ default: 0 })
  passedCases!: number;

  @Prop({ default: 0 })
  failedCases!: number;

  @Prop({ type: AggregateScoreSubDocSchema })
  aggregateScore?: AggregateScoreSubDoc;

  @Prop({ required: true })
  startedAt!: Date;

  @Prop({ type: Date, default: null })
  finishedAt?: Date | null;

  @Prop({ type: Number, default: null })
  durationMs?: number | null;

  @Prop({ default: 1 })
  schemaVersion!: number;
}

export const EvalRunSchema = SchemaFactory.createForClass(EvalRun);

EvalRunSchema.index({ evalRunId: 1 }, { unique: true, name: 'eval_runs_id_unique_idx' });
EvalRunSchema.index({ datasetId: 1, startedAt: -1 }, { name: 'eval_runs_datasetId_startedAt_idx' });
EvalRunSchema.index({ status: 1 }, { name: 'eval_runs_status_idx' });
