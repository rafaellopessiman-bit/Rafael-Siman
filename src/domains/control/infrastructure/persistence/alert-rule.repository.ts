import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { AlertRule, AlertRuleDocument } from './alert-rule.schema';
import {
  IAlertRuleRepository,
} from '../../domain/repositories/alert-rule.repository.interface';
import { IAlertRule } from '../../domain/interfaces/alert.interface';

@Injectable()
export class MongooseAlertRuleRepository implements IAlertRuleRepository {
  constructor(
    @InjectModel(AlertRule.name)
    private readonly model: Model<AlertRuleDocument>,
  ) {}

  async findById(id: string): Promise<IAlertRule | null> {
    const doc = await this.model.findOne({ ruleId: id }).lean();
    return doc ? this.toEntity(doc) : null;
  }

  async findActive(): Promise<IAlertRule[]> {
    const docs = await this.model.find({ isActive: true }).lean();
    return docs.map((d) => this.toEntity(d));
  }

  async findAll(): Promise<IAlertRule[]> {
    const docs = await this.model.find().lean();
    return docs.map((d) => this.toEntity(d));
  }

  async upsert(rule: IAlertRule): Promise<IAlertRule> {
    const doc = await this.model
      .findOneAndUpdate(
        { ruleId: rule.id },
        {
          $set: {
            ruleId: rule.id,
            name: rule.name,
            metric: rule.metric,
            operator: rule.operator,
            threshold: rule.threshold,
            windowMinutes: rule.windowMinutes,
            isActive: rule.isActive,
            schemaVersion: 1,
          },
        },
        { upsert: true, new: true },
      )
      .lean();
    return this.toEntity(doc!);
  }

  async deactivate(id: string): Promise<void> {
    await this.model.updateOne({ ruleId: id }, { $set: { isActive: false } });
  }

  private toEntity(doc: Record<string, unknown>): IAlertRule {
    return {
      id: doc['ruleId'] as string,
      name: doc['name'] as string,
      metric: doc['metric'] as IAlertRule['metric'],
      operator: doc['operator'] as IAlertRule['operator'],
      threshold: doc['threshold'] as number,
      windowMinutes: doc['windowMinutes'] as number,
      isActive: doc['isActive'] as boolean,
      schemaVersion: doc['schemaVersion'] as number,
    };
  }
}
