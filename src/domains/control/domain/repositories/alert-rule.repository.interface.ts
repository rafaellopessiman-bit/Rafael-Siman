import { IAlertRule } from '../interfaces/alert.interface';

export const ALERT_RULE_REPOSITORY = Symbol('ALERT_RULE_REPOSITORY');

export interface IAlertRuleRepository {
  findById(id: string): Promise<IAlertRule | null>;
  findActive(): Promise<IAlertRule[]>;
  findAll(): Promise<IAlertRule[]>;
  upsert(rule: IAlertRule): Promise<IAlertRule>;
  deactivate(id: string): Promise<void>;
}
