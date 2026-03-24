import { Type } from 'class-transformer';
import {
  IsArray,
  IsInt,
  IsObject,
  IsOptional,
  IsString,
  Max,
  Min,
  MinLength,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class ExtractDto {
  @ApiProperty({
    description: 'Pergunta ou instrucao de extracao em linguagem natural',
    minLength: 3,
  })
  @IsString()
  @MinLength(3)
  query!: string;

  @ApiProperty({
    description: 'JSON Schema do objeto de saida esperado',
    type: Object,
  })
  @IsObject()
  outputSchema!: Record<string, unknown>;

  @ApiPropertyOptional({
    description: 'Lista opcional de sourceFiles para restringir a extracao',
    type: [String],
  })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  sourceIds?: string[];

  @ApiPropertyOptional({
    description: 'Numero maximo de fontes consideradas na extracao (1-10)',
    default: 3,
  })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(10)
  @Type(() => Number)
  maxSources?: number;
}

export interface ExtractResponse {
  data: Record<string, unknown>;
  sources: string[];
  validJson: boolean;
  schemaValid: boolean;
  validationErrors: string[];
}
