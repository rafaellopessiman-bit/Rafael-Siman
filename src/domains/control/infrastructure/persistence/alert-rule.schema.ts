import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type AlertRuleDocument = HydratedDocument<AlertRule>;

@Schema({
  collection: 'alert_rules',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class AlertRule {
  @Prop({ required: true, unique: true })
  ruleId!: string;

  @Prop({ required: true })
  name!: string;

  @Prop({
    required: true,
    enum: [
      'avg_latency_ms',
      'p95_latency_ms',
      'guardrail_block_rate',
      'error_rate',
      'tool_error_rate',
      'eval_overall_score',
    ],
  })
  metric!: string;

  @Prop({ required: true, enum: ['gt', 'gte', 'lt', 'lte'] })
  operator!: string;

  @Prop({ required: true })
  threshold!: number;

  @Prop({ required: true, default: 60, min: 1 })
  windowMinutes!: number;

  @Prop({ required: true, default: true })
  isActive!: boolean;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const AlertRuleSchema = SchemaFactory.createForClass(AlertRule);

AlertRuleSchema.index(
  { ruleId: 1 },
  { unique: true, name: 'alert_rules_ruleId_unique_idx' },
);

AlertRuleSchema.index(
  { isActive: 1, metric: 1 },
  { name: 'alert_rules_isActive_metric_idx' },
);
