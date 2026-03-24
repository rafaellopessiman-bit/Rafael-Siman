import { IsString, IsOptional, IsInt, Min, Max, MinLength } from 'class-validator';
import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class SearchQueryDto {
  @ApiProperty({ description: 'Texto de busca', minLength: 2 })
  @IsString()
  @MinLength(2)
  q!: string;

  @ApiPropertyOptional({ description: 'Número máximo de resultados (1–50)', default: 5 })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(50)
  @Type(() => Number)
  limit?: number;
}
