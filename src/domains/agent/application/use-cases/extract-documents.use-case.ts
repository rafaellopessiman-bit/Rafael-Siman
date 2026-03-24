import { Inject, Injectable } from '@nestjs/common';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../../knowledge/domain/repositories/knowledge.repository.interface';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import { ExtractDto, ExtractResponse } from '../dtos/extract.dto';

@Injectable()
export class ExtractDocumentsUseCase {
  constructor(
    private readonly toolRegistry: ToolRegistryService,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepository: IKnowledgeRepository,
  ) {}

  async execute(dto: ExtractDto): Promise<ExtractResponse> {
    const sources = await this.resolveSources(dto);
    const rawResult = await this.toolRegistry.dispatch('extract_structured_data', {
      query: dto.query,
      schema: JSON.stringify(dto.outputSchema),
      sourceIds: sources,
      maxSources: dto.maxSources ?? 3,
    });

    const parsed = this.tryParseJson(rawResult);
    const validationErrors = parsed
      ? this.validateAgainstSchema(parsed, dto.outputSchema)
      : ['A resposta do extrator nao retornou JSON valido.'];

    return {
      data: parsed ?? { rawResult },
      sources,
      validJson: Boolean(parsed),
      schemaValid: parsed ? validationErrors.length === 0 : false,
      validationErrors,
    };
  }

  private async resolveSources(dto: ExtractDto): Promise<string[]> {
    if (dto.sourceIds && dto.sourceIds.length > 0) {
      const docs = await Promise.all(
        dto.sourceIds.map((sourceId) =>
          this.knowledgeRepository.findBySourceFile(sourceId),
        ),
      );

      return [...new Set(docs.flat().map((doc) => doc.sourceFile))];
    }

    const docs = await this.knowledgeRepository.searchText(
      dto.query,
      dto.maxSources ?? 3,
    );

    return [
      ...new Set(
        docs
          .map((doc) => doc.sourceFile)
          .filter((sourceFile): sourceFile is string => Boolean(sourceFile)),
      ),
    ];
  }

  private tryParseJson(rawResult: string): Record<string, unknown> | null {
    const sanitized = rawResult
      .trim()
      .replace(/^```json\s*/i, '')
      .replace(/^```\s*/i, '')
      .replace(/\s*```$/, '');

    try {
      return JSON.parse(sanitized) as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  private validateAgainstSchema(
    payload: Record<string, unknown>,
    schema: Record<string, unknown>,
  ): string[] {
    return this.validateValue(payload, schema, '$');
  }

  private validateValue(
    value: unknown,
    schema: Record<string, unknown>,
    path: string,
  ): string[] {
    const errors: string[] = [];

    // oneOf: exactly one sub-schema must validate without errors
    if (Array.isArray(schema.oneOf)) {
      const subSchemas = schema.oneOf.filter(
        (s): s is Record<string, unknown> => typeof s === 'object' && s !== null,
      );
      const matchCount = subSchemas.filter(
        (sub) => this.validateValue(value, sub, path).length === 0,
      ).length;

      if (matchCount !== 1) {
        errors.push(
          `${path}: deveria satisfazer exatamente 1 sub-schema de oneOf, ${matchCount} corresponderam`,
        );
      }
      return errors;
    }

    const schemaType = typeof schema.type === 'string' ? schema.type : undefined;

    // enum constraint
    if (Array.isArray(schema.enum)) {
      if (!schema.enum.includes(value)) {
        errors.push(
          `${path}: valor "${String(value)}" nao esta entre os permitidos [${schema.enum.map(String).join(', ')}]`,
        );
      }
    }

    if (schemaType && !this.matchesType(value, schemaType)) {
      errors.push(
        `${path}: deveria ser ${schemaType}, recebido ${this.describeType(value)}`,
      );
      return errors;
    }

    // string constraints
    if (schemaType === 'string' && typeof value === 'string') {
      if (typeof schema.minLength === 'number' && value.length < schema.minLength) {
        errors.push(`${path}: comprimento ${value.length} menor que minLength ${schema.minLength}`);
      }
      if (typeof schema.maxLength === 'number' && value.length > schema.maxLength) {
        errors.push(`${path}: comprimento ${value.length} maior que maxLength ${schema.maxLength}`);
      }
    }

    // number constraints
    if ((schemaType === 'number' || schemaType === 'integer') && typeof value === 'number') {
      if (typeof schema.minimum === 'number' && value < schema.minimum) {
        errors.push(`${path}: valor ${value} menor que minimum ${schema.minimum}`);
      }
      if (typeof schema.maximum === 'number' && value > schema.maximum) {
        errors.push(`${path}: valor ${value} maior que maximum ${schema.maximum}`);
      }
    }

    // array validation
    if (schemaType === 'array' && Array.isArray(value)) {
      if (typeof schema.minItems === 'number' && value.length < schema.minItems) {
        errors.push(`${path}: ${value.length} itens, minimo exigido ${schema.minItems}`);
      }
      if (typeof schema.maxItems === 'number' && value.length > schema.maxItems) {
        errors.push(`${path}: ${value.length} itens, maximo permitido ${schema.maxItems}`);
      }

      const itemsSchema = this.asRecord2(schema.items);
      if (itemsSchema) {
        for (let i = 0; i < value.length; i++) {
          errors.push(
            ...this.validateValue(value[i], itemsSchema, `${path}[${i}]`),
          );
        }
      }
    }

    // object validation (recursive)
    if (schemaType === 'object' || (!schemaType && typeof schema.properties === 'object')) {
      if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        if (schemaType === 'object') {
          errors.push(`${path}: deveria ser object, recebido ${this.describeType(value)}`);
        }
        return errors;
      }

      const payload = value as Record<string, unknown>;
      const properties = this.asRecord(schema.properties);
      const required = Array.isArray(schema.required)
        ? schema.required.filter((v): v is string => typeof v === 'string')
        : [];

      for (const field of required) {
        if (!(field in payload) || payload[field] == null) {
          errors.push(`${path}.${field}: campo obrigatorio ausente`);
        }
      }

      for (const [field, propertySchema] of Object.entries(properties)) {
        const fieldValue = payload[field];
        if (fieldValue == null) {
          continue;
        }
        errors.push(
          ...this.validateValue(fieldValue, propertySchema, `${path}.${field}`),
        );
      }
    }

    return errors;
  }

  private asRecord(value: unknown): Record<string, Record<string, unknown>> {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return {};
    }

    return value as Record<string, Record<string, unknown>>;
  }

  private asRecord2(value: unknown): Record<string, unknown> | null {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return null;
    }
    return value as Record<string, unknown>;
  }

  private matchesType(value: unknown, expectedType: string): boolean {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string';
      case 'number':
      case 'integer':
        return typeof value === 'number' && Number.isFinite(value);
      case 'boolean':
        return typeof value === 'boolean';
      case 'array':
        return Array.isArray(value);
      case 'object':
        return typeof value === 'object' && value !== null && !Array.isArray(value);
      default:
        return true;
    }
  }

  private describeType(value: unknown): string {
    if (Array.isArray(value)) {
      return 'array';
    }

    if (value === null) {
      return 'null';
    }

    return typeof value;
  }
}
