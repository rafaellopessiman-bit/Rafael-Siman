import { Injectable, BadRequestException } from '@nestjs/common';
import { TabularQueryDto } from '../dtos/tabular-query.dto';

const FORBIDDEN_KEYWORDS = [
  'INSERT',
  'UPDATE',
  'DELETE',
  'DROP',
  'ALTER',
  'TRUNCATE',
  'CREATE',
  'REPLACE',
  'MERGE',
  'EXEC',
  'EXECUTE',
] as const;

@Injectable()
export class ExecuteTabularQueryUseCase {
  execute(dto: TabularQueryDto): { sql: string; message: string } {
    this.validateSelectOnly(dto.sql);

    // TODO: integrar com engine tabular real quando disponível
    return {
      sql: dto.sql,
      message: 'Query validada. Engine tabular ainda não implementada.',
    };
  }

  private validateSelectOnly(sql: string): void {
    const normalized = sql.replace(/--.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '').trim();
    const upperSql = normalized.toUpperCase();

    if (!upperSql.startsWith('SELECT')) {
      throw new BadRequestException(
        'Apenas queries SELECT são permitidas.',
      );
    }

    for (const keyword of FORBIDDEN_KEYWORDS) {
      const pattern = new RegExp(`\\b${keyword}\\b`, 'i');
      if (pattern.test(normalized)) {
        throw new BadRequestException(
          `Operação '${keyword}' não é permitida. Apenas SELECT é aceito.`,
        );
      }
    }
  }
}
