import { IsString, IsOptional, IsEnum, IsInt, Min } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { DocumentStatus } from '@/domains/shared/enums';

export class UpsertIndexDto {
  @ApiProperty({ description: 'Caminho do arquivo de origem' })
  @IsString()
  sourceFile!: string;

  @ApiPropertyOptional({ enum: DocumentStatus, description: 'Status do documento' })
  @IsOptional()
  @IsEnum(DocumentStatus)
  status?: DocumentStatus;

  @ApiPropertyOptional({ description: 'Hash do arquivo' })
  @IsOptional()
  @IsString()
  fileHash?: string;

  @ApiPropertyOptional({ description: 'Número de chunks gerados' })
  @IsOptional()
  @IsInt()
  @Min(0)
  chunkCount?: number;

  @ApiPropertyOptional({ description: 'Total de caracteres do documento' })
  @IsOptional()
  @IsInt()
  @Min(0)
  totalChars?: number;
}
