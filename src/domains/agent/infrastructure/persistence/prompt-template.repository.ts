import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import {
  PromptTemplate,
  PromptTemplateDocument,
} from './prompt-template.schema';
import {
  IPromptTemplateRepository,
  CreatePromptTemplateData,
} from '../../domain/repositories/prompt-template.repository.interface';

@Injectable()
export class MongoosePromptTemplateRepository
  implements IPromptTemplateRepository
{
  constructor(
    @InjectModel(PromptTemplate.name)
    private readonly model: Model<PromptTemplateDocument>,
  ) {}

  async create(
    data: CreatePromptTemplateData,
  ): Promise<PromptTemplateDocument> {
    return this.model.create({
      ...data,
      isActive: true,
      schemaVersion: 1,
    });
  }

  async findBySlug(slug: string): Promise<PromptTemplateDocument | null> {
    return this.model.findOne({ slug, isActive: true });
  }

  async findAll(onlyActive = true): Promise<PromptTemplateDocument[]> {
    const filter = onlyActive ? { isActive: true } : {};
    return this.model.find(filter).sort({ name: 1 });
  }

  async update(
    slug: string,
    data: Partial<CreatePromptTemplateData>,
  ): Promise<PromptTemplateDocument | null> {
    return this.model.findOneAndUpdate(
      { slug, isActive: true },
      { $set: { ...data, updatedAt: new Date() } },
      { new: true },
    );
  }

  async deactivate(slug: string): Promise<void> {
    await this.model.updateOne(
      { slug },
      { $set: { isActive: false, updatedAt: new Date() } },
    );
  }
}
