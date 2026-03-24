import { Injectable, Inject, OnModuleInit } from '@nestjs/common';
import {
  IAgentTool,
  ToolParametersSchema,
} from '../../domain/interfaces/agent-tool.interface';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import {
  KNOWLEDGE_REPOSITORY,
  IKnowledgeRepository,
} from '../../../knowledge/domain/repositories/knowledge.repository.interface';
import {
  GroqClientService,
} from '../../../llm/infrastructure/groq/groq-client.service';

/**
 * Tool: extract_structured_data
 *
 * Busca documentos relevantes e pede ao LLM para extrair dados estruturados
 * seguindo um JSON Schema fornecido. Util para extracao de entidades,
 * campos de formularios e dados tabulares de documentos textuais.
 */
@Injectable()
export class ExtractStructuredDataTool implements IAgentTool, OnModuleInit {
  readonly name = 'extract_structured_data';
  readonly description =
    'Busca documentos e extrai dados estruturados usando um JSON Schema fornecido. Retorna um JSON com os campos preenchidos a partir do conteudo documental.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description:
          'Pergunta ou topico para buscar os documentos relevantes para extracao',
        required: true,
      },
      schema: {
        type: 'string',
        description:
          'JSON Schema (como string) descrevendo os campos a extrair. Ex: {"type":"object","properties":{"nome":{"type":"string"},"valor":{"type":"number"}},"required":["nome"]}',
        required: true,
      },
      sourceIds: {
        type: 'array',
        description:
          'Lista opcional de sourceFiles para restringir a extracao a documentos especificos',
      },
      maxSources: {
        type: 'number',
        description: 'Numero maximo de documentos a usar para extracao (1-5, padrao: 3)',
      },
    },
    required: ['query', 'schema'],
  };

  constructor(
    private readonly registry: ToolRegistryService,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepo: IKnowledgeRepository,
    private readonly groqClient: GroqClientService,
  ) {}

  onModuleInit(): void {
    this.registry.register(this);
  }

  async execute(params: Record<string, unknown>): Promise<string> {
    const query = String(params.query ?? '');
    const schemaStr = String(params.schema ?? '{}');
    const maxSources = Math.min(Math.max(Number(params.maxSources) || 3, 1), 5);
    const sourceIds = Array.isArray(params.sourceIds)
      ? params.sourceIds.map((sourceId) => String(sourceId)).filter(Boolean)
      : [];

    if (!query) {
      return 'Erro: query e obrigatoria.';
    }

    const docs = sourceIds.length > 0
      ? (await Promise.all(
          sourceIds.map((sourceId) => this.knowledgeRepo.findBySourceFile(sourceId)),
        )).flat().slice(0, maxSources)
      : await this.knowledgeRepo.searchText(query, maxSources);

    if (docs.length === 0) {
      return `Nenhum documento encontrado para extracao com query: "${query}"`;
    }

    // Concatena conteudo dos documentos (limita para nao estourar context)
    const context = docs
      .map((d) => d.content.slice(0, 2000))
      .join('\n---\n');

    // Pede ao LLM para extrair
    const extractionPrompt = `Extraia os dados solicitados dos documentos abaixo e retorne APENAS um JSON valido seguindo o schema fornecido. Se um campo nao puder ser preenchido, use null.

Schema:
${schemaStr}

Documentos:
${context}

Responda SOMENTE com o JSON, sem explicacao.`;

    const result = await this.groqClient.chatCompletion([
      { role: 'system', content: 'Voce e um extrator de dados estruturados. Retorne APENAS JSON valido.' },
      { role: 'user', content: extractionPrompt },
    ]);

    return result.content;
  }
}
