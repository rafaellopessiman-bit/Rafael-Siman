import { Type } from 'class-transformer';
import {
  IsEnum,
  IsInt,
  IsOptional,
  IsString,
  Max,
  Min,
  MinLength,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export enum CitationMode {
  INLINE = 'inline',
  SOURCES = 'sources',
  NONE = 'none',
}

export class AskDto {
  @ApiProperty({
    description: 'Pergunta em linguagem natural para a surface Ask',
    minLength: 4,
  })
  @IsString()
  @MinLength(4)
  query!: string;

  @ApiPropertyOptional({
    description: 'Numero maximo de chunks de contexto a recuperar (1-20)',
    default: 5,
  })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(20)
  @Type(() => Number)
  topK?: number;

  @ApiPropertyOptional({
    description: 'Modo de exposicao das citacoes no payload de resposta',
    enum: CitationMode,
    default: CitationMode.SOURCES,
  })
  @IsOptional()
  @IsEnum(CitationMode)
  citationMode?: CitationMode;
}

export interface AskCitation {
  index: number;
  sourceFile: string;
}

export interface AskResponse {
  answer: string;
  citations: AskCitation[];
  grounded: boolean;
  cached: boolean;
  tokensUsed: number;
  latencyMs: number;
}
