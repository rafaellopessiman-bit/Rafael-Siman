import { Injectable } from '@nestjs/common';
import { createHash } from 'crypto';

@Injectable()
export class AskCacheService {
  buildKey(query: string, topK: number, citationMode?: string): string {
    const normalized = query.trim().toLowerCase();
    const hash = createHash('sha256')
      .update(`${normalized}:${topK}:${citationMode ?? 'default'}`)
      .digest('hex')
      .slice(0, 16);
    return `ask:${hash}`;
  }
}
