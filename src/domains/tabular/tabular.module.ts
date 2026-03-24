import { Module } from '@nestjs/common';
import { TabularController } from './infrastructure/http/tabular.controller';
import { ExecuteTabularQueryUseCase } from './application/use-cases/execute-tabular-query.use-case';

@Module({
  controllers: [TabularController],
  providers: [ExecuteTabularQueryUseCase],
})
export class TabularModule {}
