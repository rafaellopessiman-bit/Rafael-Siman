import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import {
  KnowledgeDocument,
  KnowledgeDocumentDocument,
} from './knowledge-document.schema';
import {
  IKnowledgeRepository,
  CreateKnowledgeDocumentData,
} from '../../domain/repositories/knowledge.repository.interface';

@Injectable()
export class MongooseKnowledgeRepository implements IKnowledgeRepository {
  constructor(
    @InjectModel(KnowledgeDocument.name)
    private readonly knowledgeModel: Model<KnowledgeDocumentDocument>,
  ) {}

  async create(
    doc: CreateKnowledgeDocumentData,
  ): Promise<KnowledgeDocumentDocument> {
    return this.knowledgeModel.create(doc);
  }

  async findBySourceFile(
    sourceFile: string,
  ): Promise<KnowledgeDocumentDocument[]> {
    return this.knowledgeModel
      .find({ sourceFile, isActive: true })
      .sort({ chunkIndex: 1 })
      .exec();
  }

  async searchText(
    query: string,
    limit: number,
  ): Promise<KnowledgeDocumentDocument[]> {
    return this.knowledgeModel
      .find(
        { $text: { $search: query }, isActive: true },
        { score: { $meta: 'textScore' } },
      )
      .sort({ score: { $meta: 'textScore' } })
      .limit(limit)
      .exec();
  }

  async vectorSearch(
    embedding: number[],
    limit: number,
  ): Promise<KnowledgeDocumentDocument[]> {
    const results = await this.knowledgeModel
      .aggregate([
        {
          $vectorSearch: {
            index: 'knowledge_documents_embedding_vs_idx',
            path: 'embedding',
            queryVector: embedding,
            numCandidates: limit * 10,
            limit,
            filter: { isActive: true },
          },
        },
        {
          $addFields: {
            score: { $meta: 'vectorSearchScore' },
          },
        },
      ])
      .exec();

    return results as KnowledgeDocumentDocument[];
  }

  async deleteBySourceFile(sourceFile: string): Promise<number> {
    const result = await this.knowledgeModel
      .deleteMany({ sourceFile })
      .exec();
    return result.deletedCount;
  }
}
