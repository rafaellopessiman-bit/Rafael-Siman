import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';
import { DocumentStatus } from '../../../shared/enums';

export type DocumentIndexDocument = HydratedDocument<DocumentIndex>;

@Schema({
  collection: 'document_index',
  timestamps: { createdAt: 'createdAt', updatedAt: 'updatedAt' },
})
export class DocumentIndex {
  @Prop({ required: true, unique: true })
  sourceFile!: string;

  @Prop({ required: true, enum: Object.values(DocumentStatus) })
  status!: DocumentStatus;

  @Prop()
  fileHash?: string;

  @Prop({ min: 0 })
  chunkCount?: number;

  @Prop({ min: 0 })
  totalChars?: number;

  @Prop()
  lastIndexedAt?: Date;

  @Prop()
  errorMessage?: string;

  @Prop({ required: true, default: 1, min: 1 })
  schemaVersion!: number;
}

export const DocumentIndexSchema =
  SchemaFactory.createForClass(DocumentIndex);

// --- Índices ---

// Unique por arquivo-fonte
DocumentIndexSchema.index(
  { sourceFile: 1 },
  { unique: true, name: 'document_index_sourceFile_unique_idx' },
);

// Filtragem por status + ordenação por última indexação
DocumentIndexSchema.index(
  { status: 1, lastIndexedAt: -1 },
  { name: 'document_index_status_lastIndexedAt_idx' },
);
