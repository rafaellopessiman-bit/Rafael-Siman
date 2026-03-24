import { IsString, IsOptional, IsEnum, IsInt, Min } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { FileType } from '@/domains/shared/enums';

export class IndexDocumentDto {
  @ApiProperty({ description: 'Caminho do arquivo de origem' })
  @IsString()
  sourceFile!: string;

  @ApiProperty({ description: 'Conteúdo textual do documento' })
  @IsString()
  content!: string;

  @ApiPropertyOptional({ enum: FileType, description: 'Tipo do arquivo' })
  @IsOptional()
  @IsEnum(FileType)
  fileType?: FileType;

  @ApiPropertyOptional({ description: 'Índice do chunk (0-based)' })
  @IsOptional()
  @IsInt()
  @Min(0)
  chunkIndex?: number;

  @ApiPropertyOptional({ description: 'Metadados adicionais' })
  @IsOptional()
  metadata?: Record<string, unknown>;
}
