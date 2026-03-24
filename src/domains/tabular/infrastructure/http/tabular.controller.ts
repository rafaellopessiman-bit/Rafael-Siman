import { Controller, Post, Body } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import { Public } from '../../../../shared/guards/public.decorator';
import { ExecuteTabularQueryUseCase } from '../../application/use-cases/execute-tabular-query.use-case';
import { TabularQueryDto } from '../../application/dtos/tabular-query.dto';

@ApiTags('tabular')
@Controller('tabular')
@Public()
export class TabularController {
  constructor(
    private readonly executeTabularQueryUseCase: ExecuteTabularQueryUseCase,
  ) {}

  @Post('query')
  @ApiOperation({ summary: 'Executa query SQL tabular (somente SELECT)' })
  executeQuery(@Body() dto: TabularQueryDto) {
    return this.executeTabularQueryUseCase.execute(dto);
  }
}
