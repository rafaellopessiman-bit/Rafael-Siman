import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import {
  DocumentIndex,
  DocumentIndexDocument,
} from './document-index.schema';
import {
  IDocumentIndexRepository,
  UpsertDocumentIndexData,
} from '../../domain/repositories/document-index.repository.interface';
import { DocumentStatus } from '../../../shared/enums';

@Injectable()
export class MongooseDocumentIndexRepository
  implements IDocumentIndexRepository
{
  constructor(
    @InjectModel(DocumentIndex.name)
    private readonly indexModel: Model<DocumentIndexDocument>,
  ) {}

  async upsertIndex(
    sourceFile: string,
    data: UpsertDocumentIndexData,
  ): Promise<DocumentIndexDocument> {
    return this.indexModel.findOneAndUpdate(
      { sourceFile },
      {
        $set: { ...data, updatedAt: new Date() },
        $setOnInsert: { createdAt: new Date(), schemaVersion: 1 },
      },
      { upsert: true, new: true },
    ) as Promise<DocumentIndexDocument>;
  }

  async findPending(): Promise<DocumentIndexDocument[]> {
    return this.indexModel.find({ status: DocumentStatus.PENDING }).exec();
  }

  async findAll(): Promise<DocumentIndexDocument[]> {
    return this.indexModel.find().sort({ sourceFile: 1 }).exec();
  }
}
