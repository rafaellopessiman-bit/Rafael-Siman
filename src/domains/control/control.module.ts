import { Module, OnModuleInit } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';
import {
  ToolExecution,
  ToolExecutionSchema,
} from './infrastructure/persistence/tool-execution.schema';
import {
  AlertRule,
  AlertRuleSchema,
} from './infrastructure/persistence/alert-rule.schema';
import {
  AgentRun,
  AgentRunSchema,
} from '../agent/infrastructure/persistence/agent-run.schema';
import {
  AgentDefinition,
  AgentDefinitionSchema,
} from '../agent/infrastructure/persistence/agent-definition.schema';
import {
  TOOL_EXECUTION_REPOSITORY,
} from './domain/repositories/tool-execution.repository.interface';
import {
  ALERT_RULE_REPOSITORY,
} from './domain/repositories/alert-rule.repository.interface';
import { MongooseToolExecutionRepository } from './infrastructure/persistence/tool-execution.repository';
import { MongooseAlertRuleRepository } from './infrastructure/persistence/alert-rule.repository';
import { ControlTowerService } from './domain/services/control-tower.service';
import { AgentVersioningService } from './domain/services/agent-versioning.service';
import { AlertService } from './domain/services/alert.service';
import { ControlController } from './infrastructure/http/control.controller';
import { EvaluationModule } from '../evaluation/evaluation.module';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: ToolExecution.name, schema: ToolExecutionSchema },
      { name: AlertRule.name, schema: AlertRuleSchema },
      { name: AgentRun.name, schema: AgentRunSchema },
      { name: AgentDefinition.name, schema: AgentDefinitionSchema },
    ]),
    EvaluationModule,
  ],
  controllers: [ControlController],
  providers: [
    {
      provide: TOOL_EXECUTION_REPOSITORY,
      useClass: MongooseToolExecutionRepository,
    },
    {
      provide: ALERT_RULE_REPOSITORY,
      useClass: MongooseAlertRuleRepository,
    },
    ControlTowerService,
    AgentVersioningService,
    AlertService,
  ],
  exports: [
    ControlTowerService,
    AgentVersioningService,
    AlertService,
    TOOL_EXECUTION_REPOSITORY,
    ALERT_RULE_REPOSITORY,
  ],
})
export class ControlModule implements OnModuleInit {
  constructor(
    private readonly alertService: AlertService,
  ) {}

  async onModuleInit(): Promise<void> {
    await this.alertService.seedDefaultRules();
  }
}
