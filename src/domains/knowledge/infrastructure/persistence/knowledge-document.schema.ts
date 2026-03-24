import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, CallbackWithoutResultAndOptionalError } from 'mongoose';
import { FileType } from '../../../shared/enums';

export type KnowledgeDocumentDocument = HydratedDocument<KnowledgeDocument>;

@Schema({
  collection: 'knowledge_documents',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class KnowledgeDocument {
  @Prop({ required: true })
  sourceFile!: string;

  @Prop({ required: true })
  content!: string;

  @Prop({ min: 0 })
  chunkIndex?: number;

  @Prop({ enum: Object.values(FileType) })
  fileType?: FileType;

  @Prop({ min: 0 })
  charCount?: number;

  @Prop({ type: Object })
  metadata?: Record<string, unknown>;

  @Prop({ default: true })
  isActive!: boolean;

  /**
   * Campo para vector search (Atlas Vector Search).
   * O índice vectorSearch NÃO é criado via autoIndex/ensureIndexes.
   * Deve ser criado manualmente via mongosh ou Atlas UI:
   *
   *   db.runCommand({
   *     createSearchIndex: "knowledge_documents",
   *     name: "knowledge_documents_embedding_vector_idx",
   *     type: "vectorSearch",
   *     definition: {
   *       fields: [{
   *         type: "vector",
   *         path: "embedding",
   *         numDimensions: 1536,
   *         similarity: "cosine"
   *       }]
   *     }
   *   });
   */
  @Prop({ type: [Number] })
  embedding?: number[];

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const KnowledgeDocumentSchema =
  SchemaFactory.createForClass(KnowledgeDocument);

// --- Pre-save hook: calcula charCount a partir de content.length ---
KnowledgeDocumentSchema.pre('save', function (
  this: KnowledgeDocumentDocument,
  next: CallbackWithoutResultAndOptionalError,
) {
  if (this.isModified('content')) {
    this.charCount = this.content.length;
  }
  next();
});

// --- Índices ---

// Compound unique: garante que cada chunk de um arquivo seja único
KnowledgeDocumentSchema.index(
  { sourceFile: 1, chunkIndex: 1 },
  { unique: true, name: 'knowledge_documents_sourceFile_chunkIndex_unique_idx' },
);

// Full-text search em português
KnowledgeDocumentSchema.index(
  { content: 'text' },
  { name: 'knowledge_documents_content_text_idx', default_language: 'portuguese' },
);

// Filtragem por tipo de arquivo + flag de ativação
KnowledgeDocumentSchema.index(
  { fileType: 1, isActive: 1 },
  { name: 'knowledge_documents_fileType_isActive_idx' },
);
