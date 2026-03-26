import { Body, Controller, Post } from '@nestjs/common';
import { ApiCreatedResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { SkipThrottle, Throttle } from '@nestjs/throttler';
import { ActDto, ActResponse } from '../../application/dtos/act.dto';
import { ExecuteGovernedActionUseCase } from '../../application/use-cases/execute-governed-action.use-case';

@ApiTags('act')
@Controller('act')
@SkipThrottle({ ask: true, extract: true })
@Throttle({ act: {} })
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
