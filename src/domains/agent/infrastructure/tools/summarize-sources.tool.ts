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

/**
 * Tool: summarize_sources
 *
 * Busca os N documentos mais relevantes para uma query e retorna uma
 * lista estruturada de fontes com titulo, trecho e metadados.
 *
 * Diferente do search_documents (que retorna chunks brutos para o LLM
 * processar), esta tool retorna um sumario de fontes ja formatado
 * para uso em citacoes e pelo critic_agent.
 */
@Injectable()
export class SummarizeSourcesTool implements IAgentTool, OnModuleInit {
  readonly name = 'summarize_sources';
  readonly description =
    'Busca e resume as fontes mais relevantes para uma query. Retorna lista de documentos com trechos e metadados. Ideal para gerar citacoes ou para o critic_agent verificar grounding.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      query: {
        type: 'string',
        description: 'Pergunta ou topico para buscar fontes relevantes',
        required: true,
      },
      maxSources: {
        type: 'number',
        description: 'Numero maximo de fontes a retornar (1-10, padrao: 3)',
      },
    },
    required: ['query'],
  };

  constructor(
    private readonly registry: ToolRegistryService,
    @Inject(KNOWLEDGE_REPOSITORY)
    private readonly knowledgeRepo: IKnowledgeRepository,
  ) {}

  onModuleInit(): void {
    this.registry.register(this);
  }

  async execute(params: Record<string, unknown>): Promise<string> {
    const query = String(params.query ?? '');
    const maxSources = Math.min(Math.max(Number(params.maxSources) || 3, 1), 10);

    if (!query) {
      return 'Erro: query e obrigatoria.';
    }

    const docs = await this.knowledgeRepo.searchText(query, maxSources);

    if (docs.length === 0) {
      return `Nenhuma fonte encontrada para: "${query}"`;
    }

    const sources = docs.map((doc, index) => {
      const excerpt = doc.content.slice(0, 300).replace(/\n+/g, ' ').trim();
      return [
        `[Fonte ${index + 1}]`,
        `Arquivo: ${doc.sourceFile ?? 'desconhecido'}`,
        `Trecho: "${excerpt}${doc.content.length > 300 ? '...' : ''}"`,
      ].join('\n');
    });

    return `${docs.length} fonte(s) encontrada(s) para "${query}":\n\n${sources.join('\n\n---\n\n')}`;
  }
}
