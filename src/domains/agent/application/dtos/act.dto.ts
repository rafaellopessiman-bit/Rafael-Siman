import {
  ArrayUnique,
  ArrayMinSize,
  IsArray,
  IsOptional,
  IsString,
  MinLength,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class ActDto {
  @ApiProperty({
    description: 'Intent declarativa da acao a ser executada',
    minLength: 3,
  })
  @IsString()
  @MinLength(3)
  intent!: string;

  @ApiProperty({
    description: 'Lista de acoes explicitamente permitidas para este request',
    type: [String],
  })
  @IsArray()
  @ArrayMinSize(1)
  @ArrayUnique()
  @IsString({ each: true })
  allowedActions!: string[];

  @ApiPropertyOptional({
    description: 'Identificador opcional de contexto de negocio ou conversa',
  })
  @IsOptional()
  @IsString()
  contextId?: string;
}

export interface ActResponse {
  runId: string;
  toolName: string;
  action: string;
  mode: 'live' | 'dry_run';
  status: 'success' | 'error';
  audited: boolean;
  result: string;
  resultData?: Record<string, unknown>;
  executedAt: Date;
  latencyMs: number;
}
