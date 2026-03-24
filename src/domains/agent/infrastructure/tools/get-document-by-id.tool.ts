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
 * Tool: get_document_by_id
 *
 * Recupera um documento especifico da base de conhecimento pelo ID do MongoDB.
 * Util quando o agente ja sabe qual documento acessar (por exemplo, apos
 * o search_documents retornar IDs especificos).
 */
@Injectable()
export class GetDocumentByIdTool implements IAgentTool, OnModuleInit {
  readonly name = 'get_document_by_id';
  readonly description =
    'Recupera o conteudo completo de um documento especifico pelo seu ID. Use apos identificar o ID correto via search_documents.';
  readonly parameters: ToolParametersSchema = {
    type: 'object',
    properties: {
      documentId: {
        type: 'string',
        description: 'ID do documento no banco de dados (ObjectId do MongoDB)',
        required: true,
      },
    },
    required: ['documentId'],
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
    const documentId = String(params.documentId ?? '');

    if (!documentId) {
      return 'Erro: documentId e obrigatorio.';
    }

    try {
      const docs = await this.knowledgeRepo.findBySourceFile(documentId);

      if (docs.length === 0) {
        // Tenta busca por content match como fallback
        const searched = await this.knowledgeRepo.searchText(documentId, 1);
        if (searched.length === 0) {
          return `Documento com ID "${documentId}" nao encontrado.`;
        }
        const doc = searched[0];
        return this.formatDoc(doc.sourceFile, doc.content);
      }

      const doc = docs[0];
      return this.formatDoc(doc.sourceFile, doc.content);
    } catch {
      return `Erro ao buscar documento "${documentId}". Verifique se o ID e valido.`;
    }
  }

  private formatDoc(sourceFile: string, content: string): string {
    const preview = content.length > 3000 ? content.slice(0, 3000) + '\n[...conteudo truncado]' : content;
    return `Fonte: ${sourceFile}\n\n${preview}`;
  }
}
