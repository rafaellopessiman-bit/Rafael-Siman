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
 * Tool: list_sources
 *
 * Permite ao agente listar as fontes (sourceFiles) indexadas,
 * útil para saber quais documentos existem na base de conhecimento.
 */
@Injectable()
export class ListSourcesTool implements IAgentTool, OnModuleInit {
  readonly name = 'list_sources';
  readonly description =
    'Lista os arquivos/fontes indexados na base de conhecimento. Útil para saber quais documentos estão disponíveis antes de buscar.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      sourceFile: {
        type: 'string',
        description:
          'Nome parcial do arquivo para filtrar (opcional). Se omitido, lista todos.',
      },
    },
    required: [],
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
    const sourceFile = params.sourceFile
      ? String(params.sourceFile)
      : undefined;

    if (sourceFile) {
      const docs = await this.knowledgeRepo.findBySourceFile(sourceFile);
      if (docs.length === 0) {
        return `Nenhum documento encontrado com fonte "${sourceFile}".`;
      }
      return `Fonte "${sourceFile}": ${docs.length} chunk(s) indexado(s).`;
    }

    // Lista geral — busca ampla com text search vazio retorna tudo
    const allDocs = await this.knowledgeRepo.searchText('', 50);
    const sources = [...new Set(allDocs.map((d) => d.sourceFile))];

    if (sources.length === 0) {
      return 'Nenhum documento indexado na base de conhecimento.';
    }

    return `Fontes indexadas (${sources.length}):\n${sources.map((s) => `- ${s}`).join('\n')}`;
  }
}
