import { Injectable } from '@nestjs/common';

/**
 * Chunking service — porta a política do Python legado (src/storage/chunking.py).
 *
 * Contrato:
 *  - DEFAULT_MAX_CHARS = 1000
 *  - DEFAULT_OVERLAP   = 120
 *  - Segmentação por tipo de arquivo (.md headings, .json flatten, texto por parágrafo)
 *  - Window chunks com overlap quando segmento > max_chars
 */

const DEFAULT_MAX_CHARS = 1000;
const DEFAULT_OVERLAP = 120;

export interface ChunkResult {
  text: string;
  chunkIndex: number;
}

@Injectable()
export class ChunkingService {
  chunk(
    fileType: string,
    content: string,
    maxChars = DEFAULT_MAX_CHARS,
    overlap = DEFAULT_OVERLAP,
  ): ChunkResult[] {
    if (!content || !content.trim()) return [];

    const suffix = fileType.toLowerCase();
    let segments: string[];

    if (suffix === '.md') {
      segments = this.segmentMarkdown(content);
    } else if (suffix === '.json') {
      segments = this.segmentJson(content);
    } else {
      segments = this.segmentText(content);
    }

    const chunks: string[] = [];
    for (const segment of segments) {
      const clean = segment.trim();
      if (!clean) continue;
      if (clean.length <= maxChars) {
        chunks.push(clean);
      } else {
        chunks.push(...this.windowChunks(clean, maxChars, overlap));
      }
    }

    const final =
      chunks.length > 0
        ? chunks
        : this.windowChunks(content.trim(), maxChars, overlap);

    return final.map((text, i) => ({ text, chunkIndex: i }));
  }

  // ── Segmentation strategies ─────────────────────────────────────────────

  private segmentText(text: string): string[] {
    const paragraphs = text
      .split(/\n\s*\n+/)
      .map((p) => p.trim())
      .filter(Boolean);
    return paragraphs.length > 0 ? paragraphs : [text.trim()];
  }

  private segmentMarkdown(text: string): string[] {
    const pattern = /^(#{1,6}\s+.+)$/gm;
    const parts = text.split(pattern);

    if (parts.length === 1) return this.segmentText(text);

    const segments: string[] = [];
    const preamble = parts[0]?.trim();
    if (preamble) segments.push(preamble);

    for (let i = 1; i < parts.length; i += 2) {
      const heading = parts[i]?.trim() ?? '';
      const body = parts[i + 1]?.trim() ?? '';
      segments.push(body ? `${heading}\n${body}` : heading);
    }

    return segments;
  }

  private segmentJson(text: string): string[] {
    try {
      const parsed: unknown = JSON.parse(text);
      const lines: string[] = [];
      this.flattenJson(parsed, lines, '');
      return lines.length > 0
        ? this.windowChunks(lines.join('\n'), DEFAULT_MAX_CHARS, DEFAULT_OVERLAP)
        : this.segmentText(text);
    } catch {
      return this.segmentText(text);
    }
  }

  private flattenJson(value: unknown, output: string[], prefix: string): void {
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
        this.flattenJson(child, output, prefix ? `${prefix}.${key}` : key);
      }
      return;
    }

    if (Array.isArray(value)) {
      value.forEach((child, i) => {
        this.flattenJson(child, output, `${prefix}[${i}]`);
      });
      return;
    }

    const rendered = JSON.stringify(value);
    output.push(prefix ? `${prefix}: ${rendered}` : rendered);
  }

  // ── Window chunking with overlap ────────────────────────────────────────

  private windowChunks(
    text: string,
    maxChars: number,
    overlap: number,
  ): string[] {
    const trimmed = text.trim();
    if (!trimmed) return [];
    if (trimmed.length <= maxChars) return [trimmed];

    const chunks: string[] = [];
    let start = 0;

    while (start < trimmed.length) {
      const end = Math.min(start + maxChars, trimmed.length);
      const chunk = trimmed.slice(start, end).trim();
      if (chunk) chunks.push(chunk);
      if (end >= trimmed.length) break;
      start = end - overlap;
    }

    return chunks;
  }
}
