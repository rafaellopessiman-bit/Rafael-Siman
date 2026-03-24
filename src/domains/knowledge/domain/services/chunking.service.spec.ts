import { ChunkingService, ChunkResult } from './chunking.service';

describe('ChunkingService', () => {
  let service: ChunkingService;

  beforeEach(() => {
    service = new ChunkingService();
  });

  // ── helpers ────────────────────────────────────────────────────────────────

  const indices = (chunks: ChunkResult[]) => chunks.map((c) => c.chunkIndex);

  // ── empty / blank content ──────────────────────────────────────────────────

  describe('empty content', () => {
    it('returns [] for empty string', () => {
      expect(service.chunk('.txt', '')).toEqual([]);
    });

    it('returns [] for whitespace-only string', () => {
      expect(service.chunk('.txt', '   \n  ')).toEqual([]);
    });
  });

  // ── plain text ─────────────────────────────────────────────────────────────

  describe('plain text (.txt)', () => {
    it('keeps short content as single chunk', () => {
      const result = service.chunk('.txt', 'Hello world');
      expect(result).toHaveLength(1);
      expect(result[0].text).toBe('Hello world');
      expect(result[0].chunkIndex).toBe(0);
    });

    it('splits paragraphs (double newline)', () => {
      const content = 'First paragraph.\n\nSecond paragraph.';
      const result = service.chunk('.txt', content);
      expect(result).toHaveLength(2);
      expect(result[0].text).toBe('First paragraph.');
      expect(result[1].text).toBe('Second paragraph.');
    });

    it('assigns sequential chunkIndex values', () => {
      const content = 'P1\n\nP2\n\nP3';
      const result = service.chunk('.txt', content);
      expect(indices(result)).toEqual([0, 1, 2]);
    });

    it('window-chunks long text with overlap', () => {
      const longText = 'A'.repeat(2500);
      const result = service.chunk('.txt', longText, 1000, 120);
      // 2500 chars → chunks of 1000 with 120 overlap
      // starts: 0, 880, 1760, 2640 → 2640 >= 2500 so 3 chunks
      expect(result.length).toBeGreaterThanOrEqual(3);
      expect(indices(result)).toEqual(result.map((_, i) => i));
    });
  });

  // ── markdown ───────────────────────────────────────────────────────────────

  describe('markdown (.md)', () => {
    it('splits by headings', () => {
      const content = '# Título\nConteúdo do título.\n\n## Seção\nTexto da seção.';
      const result = service.chunk('.md', content);
      expect(result.length).toBeGreaterThanOrEqual(2);
    });

    it('includes heading in the chunk text', () => {
      const content = '# Introdução\nTexto de introdução.';
      const result = service.chunk('.md', content);
      expect(result[0].text).toContain('# Introdução');
    });

    it('falls back to paragraph split when no headings', () => {
      const content = 'Parágrafo sem heading.\n\nSegundo parágrafo.';
      const result = service.chunk('.md', content);
      expect(result).toHaveLength(2);
    });

    it('handles multi-level headings', () => {
      const content =
        '# H1\nText1\n## H2\nText2\n### H3\nText3';
      const result = service.chunk('.md', content);
      expect(result.length).toBeGreaterThanOrEqual(3);
    });
  });

  // ── JSON ───────────────────────────────────────────────────────────────────

  describe('json (.json)', () => {
    it('flattens object and produces chunks', () => {
      const obj = {
        name: 'Atlas',
        version: 1,
        features: ['search', 'llm'],
      };
      const result = service.chunk('.json', JSON.stringify(obj));
      expect(result.length).toBeGreaterThanOrEqual(1);
      // flattened output should contain key paths
      const combined = result.map((c) => c.text).join('\n');
      expect(combined).toContain('name');
    });

    it('falls back to text segmentation for invalid JSON', () => {
      const result = service.chunk('.json', 'not valid json at all');
      expect(result.length).toBeGreaterThanOrEqual(1);
    });

    it('handles empty object', () => {
      const result = service.chunk('.json', '{}');
      // empty object → no fields to flatten → falls back to text
      expect(result.length).toBeGreaterThanOrEqual(1);
    });
  });

  // ── window chunking ────────────────────────────────────────────────────────

  describe('window chunking (internal)', () => {
    it('does not produce empty chunks', () => {
      const longText = 'Word '.repeat(800); // ~4000 chars
      const result = service.chunk('.txt', longText, 1000, 120);
      result.forEach((chunk) => {
        expect(chunk.text.trim().length).toBeGreaterThan(0);
      });
    });

    it('overlap does not exceed chunk size', () => {
      const longText = 'X'.repeat(3000);
      const result = service.chunk('.txt', longText, 500, 100);
      // First chunk should start at 0, second at 400, etc.
      expect(result.length).toBeGreaterThan(1);
    });

    it('single chunk for text exactly at maxChars', () => {
      const text = 'A'.repeat(1000);
      const result = service.chunk('.txt', text, 1000, 120);
      expect(result).toHaveLength(1);
    });
  });

  // ── chunkIndex contract ────────────────────────────────────────────────────

  describe('chunkIndex contract', () => {
    it('always starts at 0', () => {
      const result = service.chunk('.txt', 'Only one chunk');
      expect(result[0].chunkIndex).toBe(0);
    });

    it('is always sequential with no gaps', () => {
      const content = 'A\n\nB\n\nC\n\nD\n\nE';
      const result = service.chunk('.txt', content);
      result.forEach((chunk, i) => {
        expect(chunk.chunkIndex).toBe(i);
      });
    });
  });
});
