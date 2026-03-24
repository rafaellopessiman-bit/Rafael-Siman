import { IsString, IsOptional, IsInt, Min, Max, MinLength } from 'class-validator';
import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class AskQueryDto {
  @ApiProperty({ description: 'Pergunta em linguagem natural', minLength: 4 })
  @IsString()
  @MinLength(4)
  query!: string;

  @ApiPropertyOptional({
    description: 'Número máximo de chunks de contexto a recuperar (1–20)',
    default: 5,
  })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(20)
  @Type(() => Number)
  topK?: number;
}

export interface AskQueryResult {
  answer: string;
  sources: string[];
  cached: boolean;
  tokensUsed: number;
  latencyMs: number;
}
