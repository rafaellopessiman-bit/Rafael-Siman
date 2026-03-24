import { IsString, IsOptional, IsInt, Min } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class LlmQueryDto {
  @ApiProperty({ description: 'Hash da query para cache lookup' })
  @IsString()
  queryHash!: string;

  @ApiPropertyOptional({ description: 'Resposta a ser cacheada' })
  @IsOptional()
  @IsString()
  response?: string;

  @ApiPropertyOptional({ description: 'Query textual original' })
  @IsOptional()
  @IsString()
  query?: string;

  @ApiPropertyOptional({ description: 'Modelo LLM utilizado' })
  @IsOptional()
  @IsString()
  model?: string;

  @ApiPropertyOptional({ description: 'Fontes utilizadas na resposta' })
  @IsOptional()
  @IsString({ each: true })
  sourcesUsed?: string[];

  @ApiPropertyOptional({ description: 'Tokens consumidos' })
  @IsOptional()
  @IsInt()
  @Min(0)
  tokensUsed?: number;

  @ApiPropertyOptional({ description: 'Latência em milissegundos' })
  @IsOptional()
  @IsInt()
  @Min(0)
  latencyMs?: number;
}
