import { Injectable, Inject } from '@nestjs/common';
import { DocumentIndexDocument } from '../../infrastructure/persistence/document-index.schema';
import {
  DOCUMENT_INDEX_REPOSITORY,
  IDocumentIndexRepository,
} from '../../domain/repositories/document-index.repository.interface';
import { UpsertIndexDto } from '../dtos/upsert-index.dto';

@Injectable()
export class UpsertDocumentIndexUseCase {
  constructor(
    @Inject(DOCUMENT_INDEX_REPOSITORY)
    private readonly indexRepository: IDocumentIndexRepository,
  ) {}

  async execute(dto: UpsertIndexDto): Promise<DocumentIndexDocument> {
    const { sourceFile, ...data } = dto;
    return this.indexRepository.upsertIndex(sourceFile, data);
  }

  async findPending(): Promise<DocumentIndexDocument[]> {
    return this.indexRepository.findPending();
  }

  async findAll(): Promise<DocumentIndexDocument[]> {
    return this.indexRepository.findAll();
  }
}
