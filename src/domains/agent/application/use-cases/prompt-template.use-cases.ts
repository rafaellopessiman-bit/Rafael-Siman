import { Injectable, Inject, NotFoundException } from '@nestjs/common';
import {
  PROMPT_TEMPLATE_REPOSITORY,
  IPromptTemplateRepository,
} from '../../domain/repositories/prompt-template.repository.interface';
import {
  CreatePromptTemplateDto,
  UpdatePromptTemplateDto,
} from '../dtos/agent.dto';

@Injectable()
export class CreatePromptTemplateUseCase {
  constructor(
    @Inject(PROMPT_TEMPLATE_REPOSITORY)
    private readonly repo: IPromptTemplateRepository,
  ) {}

  async execute(dto: CreatePromptTemplateDto) {
    return this.repo.create(dto);
  }
}

@Injectable()
export class ListPromptTemplatesUseCase {
  constructor(
    @Inject(PROMPT_TEMPLATE_REPOSITORY)
    private readonly repo: IPromptTemplateRepository,
  ) {}

  async execute() {
    return this.repo.findAll(true);
  }
}

@Injectable()
export class GetPromptTemplateUseCase {
  constructor(
    @Inject(PROMPT_TEMPLATE_REPOSITORY)
    private readonly repo: IPromptTemplateRepository,
  ) {}

  async execute(slug: string) {
    const template = await this.repo.findBySlug(slug);
    if (!template) {
      throw new NotFoundException(`Template "${slug}" não encontrado`);
    }
    return template;
  }
}

@Injectable()
export class UpdatePromptTemplateUseCase {
  constructor(
    @Inject(PROMPT_TEMPLATE_REPOSITORY)
    private readonly repo: IPromptTemplateRepository,
  ) {}

  async execute(slug: string, dto: UpdatePromptTemplateDto) {
    const updated = await this.repo.update(slug, dto);
    if (!updated) {
      throw new NotFoundException(`Template "${slug}" não encontrado`);
    }
    return updated;
  }
}

@Injectable()
export class DeactivatePromptTemplateUseCase {
  constructor(
    @Inject(PROMPT_TEMPLATE_REPOSITORY)
    private readonly repo: IPromptTemplateRepository,
  ) {}

  async execute(slug: string): Promise<void> {
    await this.repo.deactivate(slug);
  }
}
