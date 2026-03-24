import { PromptTemplateDocument } from '../../infrastructure/persistence/prompt-template.schema';

export const PROMPT_TEMPLATE_REPOSITORY = Symbol('PROMPT_TEMPLATE_REPOSITORY');

export interface CreatePromptTemplateData {
  slug: string;
  name: string;
  content: string;
  description?: string;
}

export interface IPromptTemplateRepository {
  create(data: CreatePromptTemplateData): Promise<PromptTemplateDocument>;
  findBySlug(slug: string): Promise<PromptTemplateDocument | null>;
  findAll(onlyActive?: boolean): Promise<PromptTemplateDocument[]>;
  update(
    slug: string,
    data: Partial<CreatePromptTemplateData>,
  ): Promise<PromptTemplateDocument | null>;
  deactivate(slug: string): Promise<void>;
}
