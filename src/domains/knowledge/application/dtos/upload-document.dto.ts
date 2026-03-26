import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional } from 'class-validator';

export class UploadDocumentQueryDto {
  @ApiPropertyOptional({ description: 'Metadados adicionais (JSON string)' })
  @IsOptional()
  metadata?: string;
}

/** MIME types permitidos para upload */
export const ALLOWED_MIME_TYPES = new Set([
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/json',
  'application/octet-stream', // fallback genérico — valida pela extensão
]);

/** Extensões permitidas */
export const ALLOWED_EXTENSIONS = new Set(['.txt', '.md', '.json', '.csv']);

/** Tamanho máximo: 10 MB */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;
