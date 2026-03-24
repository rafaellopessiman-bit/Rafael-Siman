import { Body, Controller, Post } from '@nestjs/common';
import { ApiCreatedResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { ActDto, ActResponse } from '../../application/dtos/act.dto';
import { ExecuteGovernedActionUseCase } from '../../application/use-cases/execute-governed-action.use-case';

@ApiTags('act')
@Controller('act')
export class ActController {
  constructor(
    private readonly executeGovernedAction: ExecuteGovernedActionUseCase,
  ) {}

  @Post()
  @ApiOperation({ summary: 'Surface Act com tools governadas e auditaveis' })
  @ApiCreatedResponse({ description: 'Execucao governada auditada da surface Act' })
  act(@Body() dto: ActDto): Promise<ActResponse> {
    return this.executeGovernedAction.execute(dto);
  }
}
